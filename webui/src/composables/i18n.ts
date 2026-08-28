/**
 * 轻量自研 i18n：zh / en 双语，扁平点号键 + {param} 插值。
 * 不引入 vue-i18n —— 仅一个 reactive locale ref 与一个查表函数。
 */
import { ref } from 'vue'

export type Locale = 'zh' | 'en'

const STORAGE_KEY = 'sherpa-locale'

export const messages: Record<Locale, Record<string, string>> = {
  zh: {
    'app.title': '声分 · 实时说话人分离与转写',
    'brand.name': '声分',
    'header.tagline': 'sherpa-diarize · 实时说话人分离与转写',
    'header.edgeTitle': '模型与推理全部在本机完成，音频不出设备',
    'header.edgeLabel': '端侧运行',
    'header.asrMode': '识别模式',
    'header.modeNone': '无 ASR',
    'header.modeNoneHint': '仅说话人分离，不做转写',
    'header.modeOffline': '离线',
    'header.modeOfflineHintReady': '整句离线转写',
    'header.modeOfflineHintNotReady': '离线模型未就绪',
    'header.modeStreaming': '流式',
    'header.modeStreamingHintReady': '实时增量识别（含预览）',
    'header.modeStreamingHintNotReady': '流式模型未就绪',
    'header.modelsNotReady': '基础模型未就绪（VAD / 说话人嵌入缺失），请先运行',
    'header.themeToggle': '切换主题',
    'header.langLabel': '语言',
    'source.tabsLabel': '音频来源',
    'source.demo': '示例音频',
    'source.upload': '上传',
    'source.mic': '录音',
    'source.placeholder': '选择示例音频…',
    'source.noDemo': '暂无示例音频',
    'source.chooseFile': '选择文件',
    'source.fileHint': '支持 WAV / MP3 / FLAC 等，自动转 16k 单声道',
    'source.micHint': '浏览器麦克风 · 16k 实时采集',
    'source.micName': '麦克风录音',
    'source.uploadFallback': '上传音频',
    'source.demoFallback': '示例音频',
    'action.connecting': '连接中…',
    'action.stopRecording': '停止录音',
    'action.abort': '中止',
    'action.restart': '重新开始',
    'action.retry': '重试',
    'action.start': '开始处理',
    'transport.fastest': '最快',
    'transport.pause': '暂停',
    'transport.play': '播放',
    'transport.backToStart': '回到开头',
    'transport.rates': '倍速',
    'timeline.title': '说话人时间轴',
    'timeline.hint': '悬停分段查看详情',
    'timeline.live': '实时处理中 · 已处理 {t}',
    'timeline.follow': '自动跟随',
    'timeline.noSpeech': '（无语音）',
    'timeline.waiting': '正在分光识别…首个分段出现后将在此着色',
    'timeline.empty': '尚无分段 — 选择音频并开始处理后，说话人色带将出现在这里',
    'timeline.noSpeechContent': '（无语音内容）',
    'transcript.title': '转写',
    'transcript.streaming': '流式识别',
    'transcript.offline': '离线转写',
    'transcript.diarizeOnly': '仅分离',
    'transcript.count': '{n} 段',
    'transcript.live': '实时',
    'transcript.emptyDone': '未识别到语音分段',
    'transcript.emptyIdle': '转写将在这里逐句呈现',
    'transcript.emptySubDone': '音频中可能没有清晰的人声，或 VAD 未命中。',
    'transcript.emptySubIdle': '流式模式下会先出现灰度预览，定型后转为正式文本。',
    'transcript.noSpeech': '（无语音内容）',
    'transcript.recognizing': '识别中',
    'transcript.partialHint': '文本尚未定型，最终结果到达后自动转为正式条目',
    'transcript.done': '全部完成 — 共识别 {n} 位说话人',
    'common.confidence': '置信 {pct}%',
    'common.speaker': '说话人 {n}',
    'mode.none': '无 ASR',
    'mode.offline': '离线转写',
    'mode.streaming': '流式转写',
    'side.title': '说话人统计',
    'side.genInProgress': '分段生成中…',
    'side.noData': '尚无说话人数据',
    'side.count': '{n} 段',
    'side.totalSpeech': '有效语音共 {t}',
    'side.speakersFound': '识别到 {n} 位说话人',
    'side.detailTitle': '处理详情',
    'side.source': '音频源',
    'side.mode': '识别模式',
    'side.conn': '连接状态',
    'side.processed': '已处理',
    'side.turns': '分段数',
    'side.speakers': '说话人数',
    'side.duration': '处理耗时',
    'side.connected': '已连接',
    'side.connecting': '连接中',
    'side.disconnected': '未连接',
    'status.connecting': '连接中',
    'status.processing': '处理中',
    'status.done': '完成',
    'status.error': '错误',
    'status.idle': '待机',
    'errors.decodeFailed': '音频解码失败，请换用其他文件（支持 WAV / MP3 / FLAC 等）',
    'errors.needDemo': '请先选择示例音频',
    'errors.demoLoadFailed': '示例音频加载失败',
    'errors.modelsFetch': '无法获取模型状态（/api/models）— 请确认后端已在 8000 端口运行',
    'session.modelsFail': '模型探测失败 (HTTP {status})',
    'session.wsCreate': '无法创建 WebSocket',
    'session.wsTimeout': '连接后端超时',
    'session.wsConnectFail': '无法连接后端服务',
    'session.wsClosed': '连接意外关闭',
    'session.wsBroken': '与后端的连接中断',
  },
  en: {
    'app.title': 'ShengFen · Real-time Speaker Diarization & Transcription',
    'brand.name': 'ShengFen',
    'header.tagline': 'sherpa-diarize · Real-time Speaker Diarization & Transcription',
    'header.edgeTitle': 'All models & inference run locally — audio never leaves this device',
    'header.edgeLabel': 'On-device',
    'header.asrMode': 'ASR mode',
    'header.modeNone': 'No ASR',
    'header.modeNoneHint': 'Diarization only, no transcription',
    'header.modeOffline': 'Offline',
    'header.modeOfflineHintReady': 'Whole-utterance offline transcription',
    'header.modeOfflineHintNotReady': 'Offline model not ready',
    'header.modeStreaming': 'Streaming',
    'header.modeStreamingHintReady': 'Incremental real-time recognition with preview',
    'header.modeStreamingHintNotReady': 'Streaming model not ready',
    'header.modelsNotReady': 'Base models not ready (VAD / speaker embedding missing) — run',
    'header.themeToggle': 'Toggle theme',
    'header.langLabel': 'Language',
    'source.tabsLabel': 'Audio source',
    'source.demo': 'Sample',
    'source.upload': 'Upload',
    'source.mic': 'Record',
    'source.placeholder': 'Choose a sample…',
    'source.noDemo': 'No samples available',
    'source.chooseFile': 'Choose file',
    'source.fileHint': 'WAV / MP3 / FLAC etc., auto-converted to 16 kHz mono',
    'source.micHint': 'Browser mic · 16 kHz live capture',
    'source.micName': 'Microphone recording',
    'source.uploadFallback': 'Uploaded audio',
    'source.demoFallback': 'Sample audio',
    'action.connecting': 'Connecting…',
    'action.stopRecording': 'Stop recording',
    'action.abort': 'Abort',
    'action.restart': 'Restart',
    'action.retry': 'Retry',
    'action.start': 'Start',
    'transport.fastest': 'Fastest',
    'transport.pause': 'Pause',
    'transport.play': 'Play',
    'transport.backToStart': 'Back to start',
    'transport.rates': 'Playback rate',
    'timeline.title': 'Speaker timeline',
    'timeline.hint': 'Hover a segment for details',
    'timeline.live': 'Live · processed {t}',
    'timeline.follow': 'Auto-follow',
    'timeline.noSpeech': '(no speech)',
    'timeline.waiting': 'Diarizing… the first segment will be colored here',
    'timeline.empty': 'No segments yet — pick an audio and start to see speaker bands here',
    'timeline.noSpeechContent': '(no speech)',
    'transcript.title': 'Transcript',
    'transcript.streaming': 'Streaming',
    'transcript.offline': 'Offline',
    'transcript.diarizeOnly': 'Diarization',
    'transcript.count': '{n} segments',
    'transcript.live': 'Live',
    'transcript.emptyDone': 'No speech segments detected',
    'transcript.emptyIdle': 'Transcripts will appear here, sentence by sentence',
    'transcript.emptySubDone': 'The audio may contain no clear speech, or VAD missed it.',
    'transcript.emptySubIdle': 'Streaming mode shows a gray preview that turns into final text.',
    'transcript.noSpeech': '(no speech)',
    'transcript.recognizing': 'Recognizing…',
    'transcript.partialHint': 'Text is not final; it becomes a formal entry when the result arrives',
    'transcript.done': 'Done — {n} speakers identified',
    'common.confidence': 'Confidence {pct}%',
    'common.speaker': 'Speaker {n}',
    'mode.none': 'No ASR',
    'mode.offline': 'Offline transcript',
    'mode.streaming': 'Streaming transcript',
    'side.title': 'Speaker stats',
    'side.genInProgress': 'Generating segments…',
    'side.noData': 'No speaker data yet',
    'side.count': '{n} segments',
    'side.totalSpeech': 'Total speech {t}',
    'side.speakersFound': '{n} speakers identified',
    'side.detailTitle': 'Processing details',
    'side.source': 'Source',
    'side.mode': 'Mode',
    'side.conn': 'Connection',
    'side.processed': 'Processed',
    'side.turns': 'Segments',
    'side.speakers': 'Speakers',
    'side.duration': 'Elapsed',
    'side.connected': 'Connected',
    'side.connecting': 'Connecting',
    'side.disconnected': 'Disconnected',
    'status.connecting': 'Connecting',
    'status.processing': 'Processing',
    'status.done': 'Done',
    'status.error': 'Error',
    'status.idle': 'Idle',
    'errors.decodeFailed': 'Audio decoding failed — please try another file (WAV / MP3 / FLAC supported)',
    'errors.needDemo': 'Please choose a sample audio first',
    'errors.demoLoadFailed': 'Failed to load sample audio',
    'errors.modelsFetch': 'Could not fetch model status (/api/models) — make sure the backend is running on port 8000',
    'session.modelsFail': 'Model probe failed (HTTP {status})',
    'session.wsCreate': 'Unable to create WebSocket',
    'session.wsTimeout': 'Backend connection timed out',
    'session.wsConnectFail': 'Unable to connect to the backend',
    'session.wsClosed': 'Connection closed unexpectedly',
    'session.wsBroken': 'Connection to the backend was lost',
  },
}

function initialLocale(): Locale {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'zh'
  } catch {
    return 'zh'
  }
}

export const locale = ref<Locale>(initialLocale())

/** 查表翻译：{name} 插值；缺失键回退 key 本身 */
export function t(key: string, params?: Record<string, string | number>): string {
  let text = messages[locale.value][key]
  if (text == null) text = key
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      text = text.replaceAll(`{${k}}`, String(v))
    }
  }
  return text
}

export function setLocale(l: Locale) {
  locale.value = l
  try {
    localStorage.setItem(STORAGE_KEY, l)
  } catch {
    /* 隐私模式等场景忽略 */
  }
  document.documentElement.lang = l
  document.title = t('app.title')
}

/* 模块加载即应用初始语言（index.html 默认 zh，无需首帧重绘） */
setLocale(locale.value)
