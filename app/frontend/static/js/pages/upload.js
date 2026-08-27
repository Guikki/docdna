"use strict";

document.addEventListener("DOMContentLoaded", function () {
    const uploadForm = document.getElementById("upload-form");
    const fileInput = document.getElementById("pdf-files");
    const dropzone = document.getElementById("upload-dropzone");
    const selectButton = document.getElementById(
        "select-files-button"
    );
    const clearButton = document.getElementById(
        "clear-files-button"
    );
    const filesSection = document.getElementById(
        "selected-files-section"
    );
    const filesList = document.getElementById(
        "selected-files-list"
    );
    const filesCount = document.getElementById(
        "selected-files-count"
    );
    const filesSize = document.getElementById(
        "selected-files-size"
    );
    const formActions = document.getElementById(
        "upload-form-actions"
    );
    const submitButton = document.getElementById(
        "upload-submit-button"
    );
    const feedback = document.getElementById(
        "upload-feedback"
    );
    const feedbackTitle = document.getElementById(
        "upload-feedback-title"
    );
    const feedbackStatus = document.getElementById(
        "upload-feedback-status"
    );
    const feedbackMessage = document.getElementById(
        "upload-feedback-message"
    );
    const progress = document.getElementById(
        "upload-progress"
    );
    const progressBar = document.getElementById(
        "upload-progress-bar"
    );
    const uploadResult = document.getElementById(
        "upload-result"
    );

    let selectedFiles = [];
    let processing = false;

    function isPdf(file) {
        return (
            file.type === "application/pdf"
            || file.name.toLowerCase().endsWith(".pdf")
        );
    }

    function fileKey(file) {
        return [
            file.name,
            file.size,
            file.lastModified,
        ].join("::");
    }

    function formatSize(bytes) {
        if (bytes < 1024) {
            return bytes + " bytes";
        }

        const kilobytes = bytes / 1024;

        if (kilobytes < 1024) {
            return kilobytes.toFixed(2) + " KB";
        }

        return (kilobytes / 1024).toFixed(2) + " MB";
    }

    function escapeHtml(value) {
        const element = document.createElement("div");
        element.textContent = String(value);

        return element.innerHTML;
    }

    function setProgress(percentage) {
        const value = Math.max(
            0,
            Math.min(percentage, 100)
        );

        progressBar.style.width = value + "%";
        feedbackStatus.textContent = Math.round(value) + "%";

        progress.setAttribute(
            "aria-valuenow",
            String(Math.round(value))
        );
    }

    function showFeedback(title, message, percentage) {
        feedback.hidden = false;
        feedbackTitle.textContent = title;
        feedbackMessage.textContent = message;

        setProgress(percentage);
    }

    function showError(message) {
        uploadResult.className =
            "upload-result upload-result--error";

        uploadResult.innerHTML =
            '<div class="upload-result__content">'
            + "<strong>Não foi possível concluir a operação.</strong>"
            + "<p>"
            + escapeHtml(message)
            + "</p>"
            + "</div>";
    }

    function clearResult() {
        uploadResult.className = "upload-result";
        uploadResult.innerHTML = "";
    }

    function renderFiles() {
        filesList.innerHTML = "";

        if (selectedFiles.length === 0) {
            filesSection.hidden = true;
            formActions.hidden = true;

            return;
        }

        filesSection.hidden = false;
        formActions.hidden = false;

        selectedFiles.forEach(function (file) {
            const item = document.createElement("article");

            item.className = "selected-file";

            item.innerHTML =
                '<div class="selected-file__left">'
                + '<div class="selected-file__icon">PDF</div>'
                + "<div>"
                + '<div class="selected-file__name">'
                + escapeHtml(file.name)
                + "</div>"
                + '<div class="selected-file__size">'
                + formatSize(file.size)
                + "</div>"
                + "</div>"
                + "</div>"
                + '<button type="button" '
                + 'class="selected-file__remove" '
                + 'data-file-key="'
                + escapeHtml(fileKey(file))
                + '">Remover</button>';

            filesList.appendChild(item);
        });

        filesList
            .querySelectorAll(".selected-file__remove")
            .forEach(function (button) {
                button.addEventListener("click", function () {
                    removeFile(button.dataset.fileKey);
                });
            });

        const totalSize = selectedFiles.reduce(
            function (total, file) {
                return total + file.size;
            },
            0
        );

        filesCount.textContent =
            selectedFiles.length === 1
                ? "1 documento"
                : selectedFiles.length + " documentos";

        filesSize.textContent = formatSize(totalSize);

        submitButton.textContent =
            selectedFiles.length === 1
                ? "Analisar documento"
                : "Analisar lote com "
                    + selectedFiles.length
                    + " documentos";
    }

    function addFiles(fileList) {
        if (processing) {
            return;
        }

        const existingKeys = new Set(
            selectedFiles.map(fileKey)
        );

        Array.from(fileList).forEach(function (file) {
            if (!isPdf(file)) {
                showError(
                    "O arquivo "
                    + file.name
                    + " não é um documento PDF."
                );

                return;
            }

            const key = fileKey(file);

            if (existingKeys.has(key)) {
                return;
            }

            existingKeys.add(key);
            selectedFiles.push(file);
        });

        renderFiles();
    }

    function removeFile(key) {
        if (processing) {
            return;
        }

        selectedFiles = selectedFiles.filter(
            function (file) {
                return fileKey(file) !== key;
            }
        );

        renderFiles();
    }

    function clearFiles() {
        if (processing) {
            return;
        }

        selectedFiles = [];
        fileInput.value = "";

        renderFiles();
        clearResult();
        feedback.hidden = true;
    }

    function openFileSelector() {
        if (!processing) {
            fileInput.click();
        }
    }

    function setProcessing(value) {
        processing = value;

        fileInput.disabled = value;
        selectButton.disabled = value;
        clearButton.disabled = value;
        submitButton.disabled = value;

        dropzone.classList.toggle(
            "upload-dropzone--disabled",
            value
        );
    }

    function extractError(payload) {
        if (!payload) {
            return "O servidor não informou o motivo do erro.";
        }

        if (typeof payload.detail === "string") {
            return payload.detail;
        }

        if (Array.isArray(payload.detail)) {
            return payload.detail
                .map(function (item) {
                    return item.msg || JSON.stringify(item);
                })
                .join(" ");
        }

        return "Não foi possível processar os documentos.";
    }

    function showBatchResult(batch) {
        const items = batch.documents
            .map(function (document) {
                if (
                    document.status === "completed"
                    && document.analysis_id
                ) {
                    return (
                        '<li class="batch-result-item">'
                        + "<div>"
                        + "<strong>"
                        + escapeHtml(document.original_filename)
                        + "</strong>"
                        + "<span>Processamento concluído</span>"
                        + "</div>"
                        + '<a class="btn btn-secondary" href="/analyses/'
                        + document.analysis_id
                        + '">Abrir análise</a>'
                        + "</li>"
                    );
                }

                return (
                    '<li class="batch-result-item '
                    + 'batch-result-item--failed">'
                    + "<div>"
                    + "<strong>"
                    + escapeHtml(document.original_filename)
                    + "</strong>"
                    + "<span>"
                    + escapeHtml(
                        document.error_message
                        || "Documento não processado."
                    )
                    + "</span>"
                    + "</div>"
                    + "</li>"
                );
            })
            .join("");

        uploadResult.className =
            "upload-result upload-result--success";

        uploadResult.innerHTML =
            '<section class="batch-result">'
            + '<div class="batch-result__header">'
            + "<div>"
            + "<strong>"
            + (
                batch.result.total_documents === 1
                    ? "Documento processado"
                    : "Lote processado"
            )
            + "</strong>"
            + "<p>"
            + batch.result.completed_documents
            + " documento(s) concluído(s) e "
            + batch.result.failed_documents
            + " documento(s) com erro."
            + "</p>"
            + "</div>"
            + '<span class="batch-result__status">'
            + escapeHtml(batch.status)
            + "</span>"
            + "</div>"
            + '<dl class="batch-result__summary">'
            + "<div><dt>ID do lote</dt><dd>"
            + escapeHtml(batch.id)
            + "</dd></div>"
            + "<div><dt>Progresso</dt><dd>"
            + batch.result.progress_percentage
            + "%</dd></div>"
            + "<div><dt>Total</dt><dd>"
            + batch.result.total_documents
            + "</dd></div>"
            + "</dl>"
            + '<ul class="batch-result__documents">'
            + items
            + "</ul>"
            + "</section>";
    }

    async function sendBatch(files) {
        const formData = new FormData();

        files.forEach(function (file) {
            formData.append("files", file);
        });

        const singleDocument = files.length === 1;

        showFeedback(
            singleDocument
                ? "Analisando documento"
                : "Analisando lote",
            singleDocument
                ? "O PDF está sendo processado pelo DocDNA."
                : "Os documentos estão sendo processados.",
            20
        );

        const response = await fetch(
            "/documents/batch-upload",
            {
                method: "POST",
                body: formData,
            }
        );

        setProgress(85);

        const payload = await response.json();

        if (!response.ok) {
            throw new Error(extractError(payload));
        }

        showFeedback(
            singleDocument
                ? "Análise concluída"
                : "Lote concluído",
            singleDocument
                ? "O documento foi processado. Abrindo o resultado."
                : "Os resultados estão disponíveis abaixo.",
            100
        );

        window.location.href = "/batches/" + payload.id;
    }

    async function handleSubmit(event) {
        event.preventDefault();

        if (
            processing
            || selectedFiles.length === 0
        ) {
            return;
        }

        clearResult();
        setProcessing(true);

        try {
            await sendBatch(selectedFiles);
        } catch (error) {
            showFeedback(
                "Processamento interrompido",
                "Não foi possível concluir a operação.",
                100
            );

            showError(
                error instanceof Error
                    ? error.message
                    : "Ocorreu um erro inesperado."
            );
        } finally {
            setProcessing(false);
        }
    }

    selectButton.addEventListener(
        "click",
        function (event) {
            event.stopPropagation();
            openFileSelector();
        }
    );

    dropzone.addEventListener(
        "click",
        function (event) {
            if (
                event.target.closest(
                    "#select-files-button"
                )
            ) {
                return;
            }

            openFileSelector();
        }
    );

    dropzone.addEventListener(
        "keydown",
        function (event) {
            if (
                event.key === "Enter"
                || event.key === " "
            ) {
                event.preventDefault();
                openFileSelector();
            }
        }
    );

    fileInput.addEventListener(
        "change",
        function () {
            addFiles(fileInput.files);
            fileInput.value = "";
        }
    );

    clearButton.addEventListener(
        "click",
        clearFiles
    );

    uploadForm.addEventListener(
        "submit",
        handleSubmit
    );

    ["dragenter", "dragover"].forEach(
        function (eventName) {
            dropzone.addEventListener(
                eventName,
                function (event) {
                    event.preventDefault();
                    event.stopPropagation();

                    if (!processing) {
                        dropzone.classList.add(
                            "dragover"
                        );
                    }
                }
            );
        }
    );

    ["dragleave", "drop"].forEach(
        function (eventName) {
            dropzone.addEventListener(
                eventName,
                function (event) {
                    event.preventDefault();
                    event.stopPropagation();

                    dropzone.classList.remove(
                        "dragover"
                    );
                }
            );
        }
    );

    dropzone.addEventListener(
        "drop",
        function (event) {
            if (processing) {
                return;
            }

            addFiles(event.dataTransfer.files);
        }
    );

    renderFiles();
});