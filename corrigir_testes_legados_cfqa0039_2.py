"""CF-QA 003.9.2 | Corrige somente 3 testes legados do DocDNA.

Execute na raiz do projeto Windows:
    python corrigir_testes_legados_cfqa0039_2_v2.py

- NUNCA modifica app/ ou código de produção.
- Faz pré-validação AST dos 3 arquivos antes de gravar qualquer um.
- Preserva todas as asserções, adicionando as novas fases ao teste de desempenho.
- Salva cópias .bak_cfqa0039_2_v2 e é idempotente.
- Não força testes a passarem: atualiza apenas contratos explícitos obsoletos.
"""

from __future__ import annotations

import ast
import re
import shutil
from pathlib import Path

TARGETS = (
    Path('tests/domain/services/test_batch_cross_validation_service_qrcode.py'),
    Path('tests/domain/use_cases/test_upload_document_use_case_performance.py'),
    Path('tests/domain/use_cases/test_upload_document_use_case_qrcode_fingerprints.py'),
)
FAKE_CLASS = '_FakePromptInjectionAnalysisService'
EXTRA_ARGUMENTS = ('barcodes', 'qr_structural_findings')
BACKUP_SUFFIX = '.bak_cfqa0039_2_v2'

# Ordem real das fases medida por UploadDocumentUseCase, mais a fase do builder OCR.
OLD_PHASES = (
    'validate_pdf',
    'prepare_upload_directory',
    'save_file',
    'sha256',
    'barcode_presence_detector',
    'barcode_numeric_line_compare',
    'barcode_numeric_line_evidence',
    'prompt_injection_analysis',
    'prompt_injection_visual_evidence',
    'ocr',
)
NEW_PHASES = ('financial_reconciliation', 'qr_structural_inspection')
INSERT_BEFORE = 'prompt_injection_analysis'


def _read(path: Path) -> str:
    return path.read_bytes().decode('utf-8')


def _newline(content: str) -> str:
    return '\r\n' if '\r\n' in content else '\n'


def _signature_patch(source: str, path: Path) -> tuple[str, bool]:
    module = ast.parse(source, filename=str(path))
    classes = [
        item for item in module.body
        if isinstance(item, ast.ClassDef) and item.name == FAKE_CLASS
    ]
    if len(classes) != 1:
        raise ValueError(f'{path}: classe {FAKE_CLASS} nao encontrada de forma unica')
    methods = [
        item for item in classes[0].body
        if isinstance(item, ast.FunctionDef) and item.name == 'analyze'
    ]
    if len(methods) != 1:
        raise ValueError(f'{path}: analyze() do fake nao encontrado de forma unica')

    method = methods[0]
    kw_only = {arg.arg for arg in method.args.kwonlyargs}
    if not {'native_text', 'ocr', 'normalized_document'}.issubset(kw_only):
        raise ValueError(f'{path}: assinatura original do fake mudou; nada sera modificado')
    missing = [arg for arg in EXTRA_ARGUMENTS if arg not in kw_only]
    if not missing:
        return source, False

    # Insercao preserva corpo do fake (e eventuais verificacoes internas).
    lines = source.splitlines(keepends=True)
    start = method.lineno - 1
    first_body = method.body[0].lineno - 1
    candidates = [
        idx for idx in range(start, first_body)
        if re.fullmatch(r'[ \t]*\)[ \t]*(?:->[ \t]*[^:]*)?:[ \t]*(?:\#.*)?\r?\n?', lines[idx])
    ]
    if len(candidates) != 1:
        raise ValueError(f'{path}: assinatura nao possui fechamento isolado; nada sera modificado')

    end = candidates[0]
    previous = end - 1
    while previous > start and not lines[previous].strip():
        previous -= 1
    if not lines[previous].rstrip().endswith(','):
        raise ValueError(f'{path}: ultimo parametro sem virgula; nada sera modificado')
    indentation = re.match(r'[ \t]*', lines[previous]).group(0)
    eol = _newline(source)
    new_lines = [f'{indentation}{arg}=None,{eol}' for arg in missing]
    lines[end:end] = new_lines
    patched = ''.join(lines)

    checked = ast.parse(patched, filename=str(path))
    checked_class = next(
        item for item in checked.body
        if isinstance(item, ast.ClassDef) and item.name == FAKE_CLASS
    )
    checked_method = next(
        item for item in checked_class.body
        if isinstance(item, ast.FunctionDef) and item.name == 'analyze'
    )
    checked_kwargs = {arg.arg for arg in checked_method.args.kwonlyargs}
    if not set(EXTRA_ARGUMENTS).issubset(checked_kwargs):
        raise AssertionError(f'{path}: os argumentos novos nao foram confirmados')
    return patched, True


def _performance_patch(source: str, path: Path) -> tuple[str, bool]:
    if path.name != 'test_upload_document_use_case_performance.py':
        return source, False

    module = ast.parse(source, filename=str(path))
    matches = []
    for item in ast.walk(module):
        if not isinstance(item, ast.Assert):
            continue
        expression = item.test
        if not isinstance(expression, ast.Compare) or len(expression.comparators) != 1:
            continue
        lst = expression.comparators[0]
        if not isinstance(lst, ast.List):
            continue
        if not all(isinstance(v, ast.Constant) and isinstance(v.value, str) for v in lst.elts):
            continue
        values = tuple(v.value for v in lst.elts)
        if 'barcode_numeric_line_evidence' in values and INSERT_BEFORE in values:
            matches.append((lst, values))
    if len(matches) != 1:
        raise ValueError(f'{path}: assert da lista de fases nao localizado de forma unica')

    lst, actual = matches[0]
    before = OLD_PHASES[:OLD_PHASES.index(INSERT_BEFORE)]
    after = OLD_PHASES[OLD_PHASES.index(INSERT_BEFORE):]
    intended = (*before, *NEW_PHASES, *after)

    if actual == intended:
        return source, False
    if tuple(value for value in actual if value not in NEW_PHASES) != OLD_PHASES:
        raise ValueError(
            f'{path}: fases legadas inesperadas. Envie esse teste para revisao antes de alterar.'
        )
    if any(actual.count(value) != 1 for value in actual):
        raise ValueError(f'{path}: fase duplicada na assercao; nada sera modificado')
    if any(value in actual and actual.index(value) != intended.index(value) for value in NEW_PHASES):
        raise ValueError(f'{path}: fase nova fora da ordem esperada; nada sera modificado')

    # Substitui apenas o literal de lista do assert, sem reescrever o restante do teste.
    lines = source.splitlines(keepends=True)
    first_line = lines[lst.lineno - 1]
    outer_indent = re.match(r'[ \t]*', first_line).group(0)
    item_indent = outer_indent + '    '
    eol = _newline(source)
    replacement = (
        '[' + eol
        + ''.join(f'{item_indent}"{phase}",{eol}' for phase in intended)
        + outer_indent + ']'
    )
    prefix = ''.join(lines[:lst.lineno - 1]) + first_line[:lst.col_offset]
    suffix = lines[lst.end_lineno - 1][lst.end_col_offset:] + ''.join(lines[lst.end_lineno:])
    patched = prefix + replacement + suffix

    new_module = ast.parse(patched, filename=str(path))
    found = []
    for item in ast.walk(new_module):
        if isinstance(item, ast.Assert) and isinstance(item.test, ast.Compare) and len(item.test.comparators) == 1:
            candidate = item.test.comparators[0]
            if isinstance(candidate, ast.List):
                elems = [e.value for e in candidate.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                if tuple(elems) == intended:
                    found.append(candidate)
    if len(found) != 1:
        raise AssertionError(f'{path}: assercao de fases atualizada nao confirmada')
    return patched, True


def _ensure_new_stages_exist_in_app(root: Path) -> None:
    use_case = root / 'app/domain/use_cases/upload_document_use_case.py'
    if not use_case.is_file():
        raise ValueError(f'Arquivo de producao nao encontrado: {use_case}')
    source = _read(use_case)
    if not all(f'"{stage}"' in source for stage in NEW_PHASES):
        raise ValueError('O UploadDocumentUseCase atual nao mede as duas fases novas; nada sera alterado')


def main() -> None:
    root = Path.cwd()
    missing = [str(path) for path in TARGETS if not path.is_file()]
    if missing:
        raise SystemExit('Execute na raiz do DocDNA. Arquivos nao encontrados:\n  ' + '\n  '.join(missing))
    _ensure_new_stages_exist_in_app(root)

    updates = []
    # PRE-FLIGHT: todos os arquivos sao preparados, analisados e validados sem escrita.
    for relative in TARGETS:
        original = _read(relative)
        updated, changed_fake = _signature_patch(original, relative)
        updated, changed_stages = _performance_patch(updated, relative)
        ast.parse(updated, filename=str(relative))
        updates.append((relative, original, updated))
        changes = []
        if changed_fake:
            changes.append('fake.analyze')
        if changed_stages:
            changes.append('fases de desempenho')
        print(f'[VALIDADO] {relative}: {", ".join(changes) if changes else "ja atualizado"}')

    # GRAVACAO: somente apos os tres arquivos serem validados.
    count = 0
    for relative, original, updated in updates:
        if original == updated:
            continue
        backup = relative.with_name(relative.name + BACKUP_SUFFIX)
        if not backup.exists():
            shutil.copy2(relative, backup)
        relative.write_bytes(updated.encode('utf-8'))
        count += 1
        print(f'[ATUALIZADO] {relative} | backup: {backup.name}')

    print(f'\nConcluido: {count} arquivo(s) atualizado(s). Nada em app/ foi modificado.')
    print('Testes direcionados:')
    print('  python -m pytest tests/domain/services/test_batch_cross_validation_service_qrcode.py tests/domain/use_cases/test_upload_document_use_case_performance.py tests/domain/use_cases/test_upload_document_use_case_qrcode_fingerprints.py -q')
    print('Suite completa:')
    print('  python -m pytest -q')


if __name__ == '__main__':
    main()
