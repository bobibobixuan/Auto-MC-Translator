document.addEventListener('DOMContentLoaded', () => {
    const START_LABEL = '开始一键翻译';
    const DEFAULT_WORKFLOW = '自动识别';

    const pickFileBtn = document.querySelector('.js-pick-file');
    const pickDirBtn = document.querySelector('.js-pick-dir');
    const openFolderBtn = document.querySelector('.js-open-folder');
    const openReportBtn = document.querySelector('.js-open-report');
    const startBtn = document.getElementById('start_btn');

    const pathInput = document.getElementById('modpack_path');
    const packNameInput = document.getElementById('pack_name');
    const apiKeyInput = document.getElementById('api_key');
    const providerSelect = document.getElementById('provider');
    const baseUrlInput = document.getElementById('base_url');
    const modelSelect = document.getElementById('model_select');
    const modelInput = document.getElementById('model');
    const sourceLangSelect = document.getElementById('source_lang');
    const targetLangSelect = document.getElementById('target_lang');
    const translationModeSelect = document.getElementById('translation_mode');
    const optimizationPresetSelect = document.getElementById('optimization_preset');
    const skipCompleteSelect = document.getElementById('skip_complete_targets');
    const reuseModeSelect = document.getElementById('reuse_mode');
    const skillSelect = document.getElementById('skill');
    const customPromptInput = document.getElementById('custom_prompt');
    const packFormatInput = document.getElementById('pack_format');
    const batchSizeInput = document.getElementById('batch_size');

    const providerNote = document.getElementById('provider_note');
    const sourceLangNote = document.getElementById('source_lang_note');
    const targetLangNote = document.getElementById('target_lang_note');
    const translationModeNote = document.getElementById('translation_mode_note');
    const optimizationPresetNote = document.getElementById('optimization_preset_note');
    const skipCompleteNote = document.getElementById('skip_complete_note');
    const skillNote = document.getElementById('skill_note');
    const reuseModeNote = document.getElementById('reuse_mode_note');

    const outputPreview = document.getElementById('output_preview');
    const statusTitle = document.getElementById('status_title');
    const statusLabel = document.getElementById('status_label');
    const statusDetail = document.getElementById('status_detail');
    const statusWorkflow = document.getElementById('status_workflow');
    const statusInputPath = document.getElementById('status_input_path');
    const statusOutputPreview = document.getElementById('status_output_preview');
    const actionNote = document.getElementById('action_note');
    const actionButtons = document.getElementById('action_buttons');
    const summaryPanel = document.getElementById('summary_panel');
    const beginnerLogContent = document.getElementById('beginner_log_content');
    const developerLogContent = document.getElementById('developer_log_content');
    const modeCards = document.querySelectorAll('.mode-card');

    let currentSocket = null;
    let currentPackPath = '';
    let currentReportPath = '';

    const translationModeDescriptions = {
        '完整翻译整个语言包': '完整模式：所有源语言条目都会重新翻译，适合首次整包汉化或严格重跑。',
        '只补全缺失项': '补全模式：只对目标语言里缺失的 key 发起翻译请求，适合已有汉化补洞。',
    };

    document.querySelectorAll('.tab-button').forEach((button) => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.tab-button').forEach((item) => item.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach((item) => item.classList.remove('active'));
            button.classList.add('active');
            document.getElementById(button.dataset.target).classList.add('active');
        });
    });

    function escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }

    function renderNote(note) {
        return escapeHtml(note || '')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
    }

    function addOptions(selectElement, options, defaultValue = null) {
        selectElement.innerHTML = '';
        options.forEach((optionValue) => {
            const option = document.createElement('option');
            option.value = optionValue;
            option.textContent = optionValue;
            if (defaultValue && optionValue === defaultValue) {
                option.selected = true;
            }
            selectElement.appendChild(option);
        });
    }

    function syncModeCards(selectId, selectedValue) {
        document.querySelectorAll(`.mode-card[data-select-target="${selectId}"]`).forEach((card) => {
            card.classList.toggle('is-active', card.dataset.modeValue === selectedValue);
        });
    }

    function updateTranslationModeNote() {
        translationModeNote.innerHTML = renderNote(translationModeDescriptions[translationModeSelect.value] || '当前翻译模式已切换。');
        syncModeCards('translation_mode', translationModeSelect.value);
    }

    async function safeFetchJson(url, options = {}) {
        const response = await fetch(url, options);
        const text = await response.text();
        let payload = {};
        if (text) {
            try {
                payload = JSON.parse(text);
            } catch {
                payload = { detail: text };
            }
        }
        if (!response.ok) {
            throw new Error(payload.detail || payload.message || `HTTP ${response.status}`);
        }
        return payload;
    }

    function setStatus(title, badgeText, tone, detail) {
        statusTitle.textContent = title;
        statusLabel.textContent = badgeText;
        statusLabel.className = `status-badge ${tone}`;
        statusDetail.textContent = detail;
    }

    function setStatusMeta(workflow, inputPath, preview) {
        statusWorkflow.textContent = workflow || DEFAULT_WORKFLOW;
        statusInputPath.textContent = inputPath || '尚未选择';
        statusOutputPreview.textContent = preview || '等待输入路径';
    }

    function setActionButtonsEnabled(enabled) {
        actionButtons.classList.toggle('disabled', !enabled);
        openFolderBtn.disabled = !enabled || !currentPackPath;
        openReportBtn.disabled = !enabled || !currentReportPath;
    }

    function appendText(target, text) {
        if (!text) {
            return;
        }
        target.textContent += `${text}\n`;
        target.scrollTop = target.scrollHeight;
    }

    function currentLanguageCode(value) {
        if (!value) {
            return '';
        }
        const parts = String(value).split(' | ');
        return parts[parts.length - 1];
    }

    function renderSummary(data = null) {
        const isPending = !data;
        const sourceLang = currentLanguageCode(sourceLangSelect.value) || 'en_us';
        const targetLang = currentLanguageCode(targetLangSelect.value) || 'zh_cn';
        const modSummaries = isPending ? [] : [...(data.mod_summaries || [])].sort((left, right) => {
            if ((right.translated_keys || 0) !== (left.translated_keys || 0)) {
                return (right.translated_keys || 0) - (left.translated_keys || 0);
            }
            return String(left.mod_name || '').localeCompare(String(right.mod_name || ''));
        });
        const projectPath = isPending ? (pathInput.value || '尚未开始任务') : (data.project_path || '尚未开始任务');
        const projectName = projectPath ? projectPath.split(/[\\/]/).pop() : '等待任务开始';
        const summaryLead = isPending
            ? `当前等待执行。项目会按 ${escapeHtml(sourceLang)} -> ${escapeHtml(targetLang)} 的方向翻译，完成后在这里汇总结果。`
            : `项目 ${escapeHtml(projectName)} 已完成翻译，以下是本次导出的模组和词条统计。`;

        const metrics = [
            ['模组总数', isPending ? '-' : String(data.mod_count ?? modSummaries.length)],
            ['实际翻译模组', isPending ? '-' : String(data.translated_mod_count ?? modSummaries.filter((item) => (item.translated_keys || 0) > 0).length)],
            ['语言文件数', isPending ? '-' : String(data.asset_count ?? 0)],
            ['翻译条数', isPending ? '-' : String(data.translated_keys ?? 0)],
            ['完整翻译跳过', isPending ? '-' : String(data.skipped_complete_assets ?? 0)],
            ['跳过项', isPending ? '-' : String(data.skipped_count ?? 0)],
        ];

        const metricCards = metrics.map(([label, value]) => `
            <div class="summary-metric">
              <span>${escapeHtml(label)}</span>
              <strong>${escapeHtml(value)}</strong>
            </div>
        `).join('');

        const rows = isPending
            ? '<tr><td colspan="5">任务完成后，会在这里列出每个模组的翻译条数和语言文件数。</td></tr>'
            : modSummaries.map((item) => `
                <tr>
                  <td>${escapeHtml(item.mod_name || '-')}</td>
                  <td>${escapeHtml(item.translated_keys ?? 0)}</td>
                  <td>${escapeHtml(item.queued_keys ?? 0)}</td>
                  <td>${escapeHtml(item.source_keys ?? 0)}</td>
                  <td>${escapeHtml(item.asset_count ?? 0)}</td>
                </tr>
            `).join('');

        const outputFolder = isPending ? '任务完成后显示' : (data.pack_folder || '任务完成后显示');
        const reportFile = isPending ? '任务完成后生成 translation_report.json' : (data.report_file || '任务完成后生成 translation_report.json');

        summaryPanel.innerHTML = `
            <div class="panel-heading compact">
              <h2>翻译项目摘要</h2>
              <p>${summaryLead}</p>
            </div>
            <div class="summary-grid">${metricCards}</div>
            <div class="summary-paths">
              <div><strong>翻译项目</strong><code>${escapeHtml(projectPath)}</code></div>
              <div><strong>导出目录</strong><code>${escapeHtml(outputFolder)}</code></div>
              <div><strong>翻译报告</strong><code>${escapeHtml(reportFile)}</code></div>
            </div>
            <div class="summary-table-wrap">
              <table class="summary-table">
                <thead>
                  <tr>
                    <th>模组</th>
                    <th>已翻译条数</th>
                    <th>待处理条数</th>
                    <th>总词条数</th>
                    <th>语言文件数</th>
                  </tr>
                </thead>
                <tbody>${rows}</tbody>
              </table>
            </div>
        `;
    }

    async function refreshFieldNotes() {
        const query = new URLSearchParams({
            source_lang: sourceLangSelect.value,
            target_lang: targetLangSelect.value,
            skill: skillSelect.value,
            skip_complete_targets: skipCompleteSelect.value,
            reuse_mode: reuseModeSelect.value,
            optimization_preset: optimizationPresetSelect.value,
        });
        const notes = await safeFetchJson(`/api/config/field-notes?${query.toString()}`);
        sourceLangNote.innerHTML = renderNote(notes.source_lang_note);
        targetLangNote.innerHTML = renderNote(notes.target_lang_note);
        updateTranslationModeNote();
        skillNote.innerHTML = renderNote(notes.skill_note);
        skipCompleteNote.innerHTML = renderNote(notes.skip_complete_note);
        reuseModeNote.innerHTML = renderNote(notes.reuse_mode_note);
        optimizationPresetNote.innerHTML = renderNote(notes.optimization_preset_note);
        syncModeCards('optimization_preset', optimizationPresetSelect.value);
    }

    async function updateProviderDetails(preferredModel = null, preferredBaseUrl = null) {
        const details = await safeFetchJson(`/api/config/provider-details?provider_label=${encodeURIComponent(providerSelect.value)}`);
        providerNote.innerHTML = renderNote(details.note);

        addOptions(modelSelect, details.models || []);
        modelSelect.appendChild(new Option('自定义模型', '__custom__'));

        const desiredModel = preferredModel || modelInput.value || details.default_model || '';
        if ((details.models || []).includes(desiredModel)) {
            modelSelect.value = desiredModel;
            modelInput.value = desiredModel;
        } else {
            modelSelect.value = '__custom__';
            modelInput.value = desiredModel;
        }

        baseUrlInput.value = preferredBaseUrl !== null ? preferredBaseUrl : (details.base_url || '');
        toggleCustomModelInput();
    }

    function toggleCustomModelInput() {
        if (modelSelect.value === '__custom__') {
            modelInput.hidden = false;
        } else {
            modelInput.hidden = true;
            modelInput.value = modelSelect.value;
        }
    }

    async function updateOptimizationPreset() {
        const preset = optimizationPresetSelect.value;
        if (!preset) {
            return;
        }
        if (preset !== '自定义') {
            const details = await safeFetchJson(`/api/config/optimization-preset-details?preset_label=${encodeURIComponent(preset)}&fallback_skip=${encodeURIComponent(skipCompleteSelect.value)}&fallback_reuse=${encodeURIComponent(reuseModeSelect.value)}`);
            skipCompleteSelect.value = details.skip_complete_targets;
            reuseModeSelect.value = details.reuse_mode;
        }
        await refreshFieldNotes();
    }

    async function handleModeCardClick(card) {
        const selectTarget = card.dataset.selectTarget;
        const modeValue = card.dataset.modeValue;
        const selectElement = document.getElementById(selectTarget);
        if (!selectElement || !modeValue) {
            return;
        }

        selectElement.value = modeValue;
        if (selectTarget === 'optimization_preset') {
            await updateOptimizationPreset();
            return;
        }

        updateTranslationModeNote();
    }

    async function updatePreview() {
        if (!pathInput.value.trim()) {
            outputPreview.textContent = '尚未选择输入路径...';
            setStatusMeta(statusWorkflow.textContent, '', '');
            return;
        }
        const query = new URLSearchParams({
            input_path: pathInput.value,
            pack_name: packNameInput.value,
            target_lang: targetLangSelect.value,
        });
        const payload = await safeFetchJson(`/api/preview-output?${query.toString()}`);
        outputPreview.textContent = payload.preview || '预览生成失败';
        setStatusMeta(statusWorkflow.textContent, pathInput.value, payload.preview || '');
    }

    async function suggestPackNameIfEmpty() {
        if (packNameInput.value.trim() || !pathInput.value.trim()) {
            return;
        }
        const query = new URLSearchParams({
            input_path: pathInput.value,
            pack_name: packNameInput.value,
            target_lang: targetLangSelect.value,
        });
        const payload = await safeFetchJson(`/api/suggest-pack-name?${query.toString()}`);
        packNameInput.value = payload.pack_name || '';
        outputPreview.textContent = payload.preview || outputPreview.textContent;
        setStatusMeta(statusWorkflow.textContent, pathInput.value, payload.preview || '');
    }

    async function openPath(path) {
        await safeFetchJson('/api/open-path', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path }),
        });
        actionNote.textContent = `已打开：${path}`;
    }

    function resetLogs() {
        beginnerLogContent.textContent = '';
        developerLogContent.textContent = '';
    }

    function resetRunState() {
        currentPackPath = '';
        currentReportPath = '';
        setActionButtonsEnabled(false);
        actionNote.textContent = '翻译完成后，你可以直接打开程序目录下的 output 文件夹或翻译报告。';
    }

    function buildPayload() {
        return {
            modpack_path: pathInput.value,
            pack_name: packNameInput.value,
            api_key: apiKeyInput.value,
            source_lang: sourceLangSelect.value,
            target_lang: targetLangSelect.value,
            pack_format: parseFloat(packFormatInput.value) || 15,
            provider: providerSelect.value,
            base_url: baseUrlInput.value,
            model: modelSelect.value === '__custom__' ? modelInput.value.trim() : modelSelect.value,
            translation_mode: translationModeSelect.value,
            skip_complete_targets: skipCompleteSelect.value,
            skill: skillSelect.value,
            reuse_mode: reuseModeSelect.value,
            batch_size: parseInt(batchSizeInput.value, 10) || 60,
            custom_prompt: customPromptInput.value,
        };
    }

    async function startTranslation() {
        if (!pathInput.value.trim()) {
            window.alert('请先选择要翻译的模组文件或目录。');
            return;
        }

        startBtn.disabled = true;
        startBtn.textContent = '任务进行中...';
        resetRunState();
        resetLogs();
        renderSummary(null);
        setStatus('准备启动', '启动中', 'running', '默认配置已就绪，正在校验输入配置。');
        setStatusMeta(DEFAULT_WORKFLOW, pathInput.value, outputPreview.textContent);

        try {
            const payload = buildPayload();
            const response = await safeFetchJson('/api/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            connectWebSocket(response.job_id);
        } catch (error) {
            setStatus('翻译失败', '错误', 'error', `请求失败：${error.message}`);
            startBtn.disabled = false;
            startBtn.textContent = START_LABEL;
        }
    }

    function connectWebSocket(jobId) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/jobs/${encodeURIComponent(jobId)}/stream`;
        currentSocket = new WebSocket(wsUrl);

        currentSocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                const data = message.data || {};

                if (message.type === 'meta') {
                    setStatus('翻译运行中', '运行中', 'running', data.detail || '输入校验完成，开始扫描语言文件。');
                    setStatusMeta(data.workflow_label, data.input_path, data.output_preview);
                    appendText(beginnerLogContent, data.beginner_log);
                    (data.developer_logs || []).forEach((line) => appendText(developerLogContent, line));
                    return;
                }

                if (message.type === 'log') {
                    appendText(developerLogContent, data.developer);
                    appendText(beginnerLogContent, data.beginner);
                    if (data.detail) {
                        statusDetail.textContent = data.detail;
                    }
                    return;
                }

                if (message.type === 'result') {
                    currentPackPath = data.pack_folder || '';
                    currentReportPath = data.report_file || '';
                    setActionButtonsEnabled(Boolean(currentPackPath || currentReportPath));
                    actionNote.textContent = '已生成导出目录，可以直接使用下方按钮打开文件夹或翻译报告。';
                    setStatus('翻译完成', '完成', 'success', data.detail || '翻译任务已完成。');
                    renderSummary(data);
                    return;
                }

                if (message.type === 'error') {
                    appendText(developerLogContent, data.developer);
                    appendText(beginnerLogContent, data.beginner);
                    setStatus('翻译失败', '错误', 'error', data.message || '任务失败');
                    resetRunState();
                    return;
                }

                if (message.type === 'finished') {
                    startBtn.disabled = false;
                    startBtn.textContent = START_LABEL;
                    if (currentSocket && currentSocket.readyState < WebSocket.CLOSING) {
                        currentSocket.close();
                    }
                }
            } catch (error) {
                console.error('WS Parse Error:', error);
            }
        };

        currentSocket.onclose = () => {
            startBtn.disabled = false;
            startBtn.textContent = START_LABEL;
        };
    }

    function setupEventListeners() {
        pickFileBtn.addEventListener('click', async () => {
            try {
                const payload = await safeFetchJson('/api/pick-path', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ current_path: pathInput.value, select_directory: false }),
                });
                if (payload.path) {
                    pathInput.value = payload.path;
                    await suggestPackNameIfEmpty();
                    await updatePreview();
                }
            } catch (error) {
                setStatus('等待开始', '错误', 'error', error.message);
            }
        });

        pickDirBtn.addEventListener('click', async () => {
            try {
                const payload = await safeFetchJson('/api/pick-path', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ current_path: pathInput.value, select_directory: true }),
                });
                if (payload.path) {
                    pathInput.value = payload.path;
                    await suggestPackNameIfEmpty();
                    await updatePreview();
                }
            } catch (error) {
                setStatus('等待开始', '错误', 'error', error.message);
            }
        });

        providerSelect.addEventListener('change', async () => {
            await updateProviderDetails();
        });

        modelSelect.addEventListener('change', () => {
            toggleCustomModelInput();
        });

        optimizationPresetSelect.addEventListener('change', async () => {
            await updateOptimizationPreset();
        });

        translationModeSelect.addEventListener('change', () => {
            updateTranslationModeNote();
        });

        skipCompleteSelect.addEventListener('change', async () => {
            optimizationPresetSelect.value = '自定义';
            await refreshFieldNotes();
        });

        reuseModeSelect.addEventListener('change', async () => {
            optimizationPresetSelect.value = '自定义';
            await refreshFieldNotes();
        });

        sourceLangSelect.addEventListener('change', refreshFieldNotes);
        targetLangSelect.addEventListener('change', async () => {
            await refreshFieldNotes();
            await updatePreview();
        });
        skillSelect.addEventListener('change', refreshFieldNotes);

        pathInput.addEventListener('change', updatePreview);
        packNameInput.addEventListener('input', updatePreview);
        startBtn.addEventListener('click', startTranslation);

        modeCards.forEach((card) => {
            card.addEventListener('click', async () => {
                await handleModeCardClick(card);
            });
        });

        openFolderBtn.addEventListener('click', async () => {
            if (currentPackPath) {
                await openPath(currentPackPath);
            }
        });

        openReportBtn.addEventListener('click', async () => {
            if (currentReportPath) {
                await openPath(currentReportPath);
            }
        });
    }

    async function init() {
        try {
            const [defaults, lookups] = await Promise.all([
                safeFetchJson('/api/config/defaults'),
                safeFetchJson('/api/config/lookups'),
            ]);

            addOptions(providerSelect, lookups.providers, defaults.provider);
            addOptions(sourceLangSelect, lookups.languages, defaults.source_lang);
            addOptions(targetLangSelect, lookups.languages, defaults.target_lang);
            addOptions(translationModeSelect, lookups.translation_modes, defaults.translation_mode);
            addOptions(optimizationPresetSelect, lookups.optimization_presets, defaults.optimization_preset);
            addOptions(skipCompleteSelect, lookups.skip_complete_targets, defaults.skip_complete_targets);
            addOptions(reuseModeSelect, lookups.reuse_modes, defaults.reuse_mode);
            addOptions(skillSelect, lookups.skills, defaults.skill);

            apiKeyInput.value = defaults.api_key || '';
            packFormatInput.value = defaults.pack_format;
            batchSizeInput.value = defaults.batch_size;
            providerNote.innerHTML = renderNote(defaults.provider_note);
            await updateProviderDetails(defaults.model, defaults.base_url);

            sourceLangNote.innerHTML = renderNote(defaults.notes.source_lang_note);
            targetLangNote.innerHTML = renderNote(defaults.notes.target_lang_note);
            translationModeNote.innerHTML = renderNote(translationModeDescriptions[defaults.translation_mode] || '当前翻译模式已切换。');
            skillNote.innerHTML = renderNote(defaults.notes.skill_note);
            skipCompleteNote.innerHTML = renderNote(defaults.notes.skip_complete_note);
            reuseModeNote.innerHTML = renderNote(defaults.notes.reuse_mode_note);
            optimizationPresetNote.innerHTML = renderNote(defaults.notes.optimization_preset_note);
            syncModeCards('translation_mode', defaults.translation_mode);
            syncModeCards('optimization_preset', defaults.optimization_preset);

            renderSummary(null);
            setStatus('等待开始', '等待运行', 'info', '选择输入路径并填写 API Key 后即可启动任务。默认结果固定保存到程序目录下的 output 文件夹。');
            setStatusMeta(DEFAULT_WORKFLOW, '', '');
            setActionButtonsEnabled(false);
            setupEventListeners();
            await updatePreview();
        } catch (error) {
            console.error('Failed to init UI:', error);
            setStatus('初始化失败', '错误', 'error', error.message);
        }
    }

    init();
});