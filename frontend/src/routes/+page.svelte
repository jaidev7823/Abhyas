<script lang="ts">
	import { api } from '$lib/api';
	import type { ComparisonResponse, ReferenceData, ScoreData } from '$lib/types';
	import UploadZone from '$lib/components/UploadZone.svelte';
	import Timeline from '$lib/components/Timeline.svelte';
	import ScoreCard from '$lib/components/ScoreCard.svelte';

	let masterFile = $state<File | null>(null);
	let masterUrl = $state<string | null>(null);
	let reference = $state<ReferenceData | null>(null);
	let attemptReference = $state<ReferenceData | null>(null);
	let score = $state<ScoreData | null>(null);

	let loading = $state(false);
	let error = $state<string | null>(null);
	let step: 'upload' | 'analyzed' | 'done' = $state('upload');

	let audioEl = $state<HTMLAudioElement | null>(null);
	let isPlaying = $state(false);
	let currentTime = $state(0);
	let rafId = $state(0);
	let masterMuted = $state(false);
	let masterVolume = $state(0.75);

	let isRecording = $state(false);
	let recordedBlob = $state<Blob | null>(null);
	let recordedUrl = $state<string | null>(null);
	let mediaRecorder = $state<MediaRecorder | null>(null);
	let recordingStopTimer = $state<number | null>(null);

	function getRecorderOptions(): MediaRecorderOptions {
		const preferredTypes = [
			'audio/webm;codecs=opus',
			'audio/ogg;codecs=opus',
			'audio/webm',
		];
		const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported(type));
		return {
			...(mimeType ? { mimeType } : {}),
			audioBitsPerSecond: 128000,
		};
	}

	function onMasterFile(file: File) {
		if (masterUrl) URL.revokeObjectURL(masterUrl);
		masterFile = file;
		masterUrl = URL.createObjectURL(file);
		reference = null;
		attemptReference = null;
		score = null;
		recordedBlob = null;
		if (recordedUrl) URL.revokeObjectURL(recordedUrl);
		recordedUrl = null;
		step = 'upload';
		cleanupAudio();
	}

	function cleanupAudio() {
		if (audioEl) {
			audioEl.pause();
			audioEl.src = '';
		}
		if (rafId) cancelAnimationFrame(rafId);
		audioEl = null;
		isPlaying = false;
		currentTime = 0;
	}

	function setupAudio(url: string) {
		cleanupAudio();
		const el = new Audio(url);
		el.preload = 'auto';
		el.volume = masterVolume;
		el.muted = masterMuted;
		el.onended = () => {
			isPlaying = false;
			currentTime = reference?.duration ?? el.currentTime;
			if (rafId) cancelAnimationFrame(rafId);
		};
		audioEl = el;
	}

	function startPlaybackLoop() {
		if (rafId) cancelAnimationFrame(rafId);
		function tick() {
			if (audioEl) currentTime = audioEl.currentTime;
			if (audioEl && !audioEl.paused) rafId = requestAnimationFrame(tick);
		}
		rafId = requestAnimationFrame(tick);
	}

	async function play() {
		if (!audioEl) return;
		await audioEl.play();
		isPlaying = true;
		startPlaybackLoop();
	}

	function pause() {
		if (audioEl) audioEl.pause();
		isPlaying = false;
		if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
	}

	function seek(t: number) {
		if (audioEl) {
			audioEl.currentTime = t;
			currentTime = t;
		}
	}

	function toggleMasterMute() {
		masterMuted = !masterMuted;
		if (audioEl) audioEl.muted = masterMuted;
	}

	function setMasterVolume(value: number) {
		masterVolume = Math.max(0, Math.min(1, value));
		if (audioEl) {
			audioEl.volume = masterVolume;
			if (masterVolume > 0 && masterMuted) {
				masterMuted = false;
				audioEl.muted = false;
			}
		}
	}

	async function analyze() {
		if (!masterFile) return;
		loading = true;
		error = null;
		try {
			const formData = new FormData();
			formData.append('audio', masterFile);
			const res = await api.post('/shadow/analyze-master', formData, {
				headers: { 'Content-Type': 'multipart/form-data' },
				timeout: 120000,
			});
			reference = res.data;
			attemptReference = null;
			step = 'analyzed';
			setupAudio(masterUrl!);
			currentTime = 0;
		} catch (e: any) {
			error = e?.response?.data?.detail || e?.message || 'Analysis failed';
		} finally {
			loading = false;
		}
	}

	async function startRecording() {
		if (!reference) return;
		let stream: MediaStream | null = null;
		let recorder: MediaRecorder | null = null;
		try {
			if (recordedUrl) URL.revokeObjectURL(recordedUrl);
			recordedBlob = null;
			recordedUrl = null;
			score = null;
			attemptReference = null;
			seek(0);

			stream = await navigator.mediaDevices.getUserMedia({
				audio: {
					echoCancellation: false,
					noiseSuppression: false,
					autoGainControl: false,
					channelCount: 1,
					sampleRate: 48000,
				},
			});
			const recorderOptions = getRecorderOptions();
			recorder = new MediaRecorder(stream, recorderOptions);
			const activeStream = stream;
			const activeRecorder = recorder;
			const chunks: BlobPart[] = [];
			recorder.ondataavailable = (e) => {
				if (e.data.size > 0) chunks.push(e.data);
			};
			recorder.onstop = () => {
				const blob = new Blob(chunks, { type: activeRecorder.mimeType || recorderOptions.mimeType || 'audio/webm' });
				recordedBlob = blob;
				if (recordedUrl) URL.revokeObjectURL(recordedUrl);
				recordedUrl = URL.createObjectURL(blob);
				activeStream.getTracks().forEach((t) => t.stop());
				if (recordingStopTimer) {
					clearTimeout(recordingStopTimer);
					recordingStopTimer = null;
				}
				isRecording = false;
			};
			recorder.start();
			mediaRecorder = recorder;
			isRecording = true;
			await play();
			recordingStopTimer = window.setTimeout(() => {
				if (activeRecorder.state === 'recording') {
					stopRecording();
				}
			}, reference.duration * 1000 + 500);
		} catch (e: any) {
			isRecording = false;
			pause();
			error = e?.name === 'NotAllowedError' ? 'Microphone access denied' : e?.message || 'Recording failed';
			if (recorder?.state === 'recording') recorder.stop();
			stream?.getTracks().forEach((t) => t.stop());
		}
	}

	function stopRecording() {
		if (mediaRecorder && mediaRecorder.state === 'recording') {
			mediaRecorder.stop();
		}
		pause();
		isRecording = false;
	}

	async function compare() {
		if (!masterFile || !recordedBlob || !reference) return;
		loading = true;
		error = null;
		try {
			const formData = new FormData();
			formData.append('master_audio', masterFile);
			const ext = recordedBlob.type.includes('ogg') ? 'ogg' : 'webm';
			formData.append('user_audio', recordedBlob, `recording.${ext}`);
			const res = await api.post('/shadow/compare-attempt', formData, {
				headers: { 'Content-Type': 'multipart/form-data' },
				timeout: 120000,
			});
			const data = res.data as ComparisonResponse;
			score = {
				overall: data.overall,
				timing: data.timing,
				pitch: data.pitch,
				rhythm: data.rhythm,
				pacing: data.pacing,
			};
			attemptReference = data.attempt ?? null;
			step = 'done';
		} catch (e: any) {
			error = e?.response?.data?.detail || e?.message || 'Comparison failed';
		} finally {
			loading = false;
		}
	}

	function resetAll() {
		if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop();
		if (masterUrl) URL.revokeObjectURL(masterUrl);
		if (recordedUrl) URL.revokeObjectURL(recordedUrl);
		cleanupAudio();
		masterFile = null;
		masterUrl = null;
		reference = null;
		attemptReference = null;
		score = null;
		recordedBlob = null;
		recordedUrl = null;
		error = null;
		step = 'upload';
	}
</script>

<div class="app">
	<header class="header">
		<h1 class="title">shadowing coach</h1>
		<p class="subtitle">speak with precision</p>
	</header>

	<main class="main">
		{#if error}
			<div class="error-banner">
				<span>{error}</span>
				<button class="dismiss" onclick={() => error = null}>×</button>
			</div>
		{/if}

		<!-- Step 1: Upload -->
		<section class="section">
			<h2 class="section-label">
				<span class="step-num">1</span>
				Upload Master Audio
			</h2>
			{#if !masterFile}
				<UploadZone onFile={onMasterFile} />
			{:else}
				<div class="file-selected">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4fc3f7" stroke-width="2">
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
						<polyline points="14 2 14 8 20 8" />
					</svg>
					<span class="file-name">{masterFile.name}</span>
					<span class="file-size">({(masterFile.size / 1024).toFixed(0)} KB)</span>
					<button class="link-btn" onclick={resetAll}>Change</button>
				</div>
				<div class="analyze-row">
					<button class="btn btn-primary" onclick={analyze} disabled={loading}>
						{#if loading}
              <span class="spinner"></span>
              Analyzing...
						{:else}
							Analyze Audio
						{/if}
					</button>
				</div>
			{/if}
		</section>

		<!-- Step 2: Blueprint + Playback -->
		{#if reference}
			<section class="section">
				<h2 class="section-label">
					<span class="step-num">2</span>
					Speaking Blueprint
				</h2>
				<Timeline
					{reference}
					comparisonReference={attemptReference}
					{currentTime}
					{isPlaying}
					{masterMuted}
					{masterVolume}
					onPlay={play}
					onPause={pause}
					onSeek={seek}
					onToggleMute={toggleMasterMute}
					onVolumeChange={setMasterVolume}
				/>
			</section>

			<!-- Step 3: Recording -->
			<section class="section">
				<h2 class="section-label">
					<span class="step-num">3</span>
					Record Your Attempt
				</h2>
				<div class="recording-area">
					{#if !recordedBlob && !isRecording}
						<button class="btn btn-record" onclick={startRecording}>
							<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
								<circle cx="12" cy="12" r="8" />
							</svg>
							Start Recording
						</button>
						<p class="hint">Max {reference.duration.toFixed(0)} seconds</p>
					{/if}

					{#if isRecording}
						<div class="recording-active">
              <div class="rec-pulse"></div>
              <span class="rec-text">Recording...</span>
							<button class="btn btn-secondary" onclick={stopRecording}>
								Stop
							</button>
						</div>
					{/if}

					{#if recordedUrl && !isRecording}
						<div class="recorded-preview">
              <audio controls src={recordedUrl} class="audio-player"></audio>
							<div class="compare-row">
								<button class="btn btn-primary" onclick={compare} disabled={loading}>
									{#if loading}
                    <span class="spinner"></span>
                    Comparing...
									{:else}
										Compare with Master
									{/if}
								</button>
								<button class="btn btn-secondary" onclick={() => {
									recordedBlob = null;
									if (recordedUrl) URL.revokeObjectURL(recordedUrl);
									recordedUrl = null;
									score = null;
									attemptReference = null;
								}}>Re-record</button>
							</div>
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<!-- Step 4: Score -->
		{#if score}
			<section class="section">
				<h2 class="section-label">
					<span class="step-num">4</span>
					Results
				</h2>
				<ScoreCard {score} />
				<div class="reset-row">
					<button class="btn btn-secondary" onclick={resetAll}>Start Over</button>
				</div>
			</section>
		{/if}
	</main>
</div>

<style>
	.app {
		max-width: 1000px;
		margin: 0 auto;
		padding: 32px 20px 64px;
		font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
	}

	.header {
		text-align: center;
		margin-bottom: 32px;
	}

	.title {
		font-size: 24px;
		font-weight: 700;
		color: #fff;
		margin: 0;
		letter-spacing: 1px;
		text-transform: uppercase;
	}

	.subtitle {
		font-size: 13px;
		color: #666;
		margin: 4px 0 0;
		letter-spacing: 2px;
		text-transform: uppercase;
	}

	.main {
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	.section {
		background: #181818;
		border-radius: 14px;
		padding: 20px 24px;
		border: 1px solid #222;
	}

	.section-label {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 14px;
		font-weight: 600;
		color: #ccc;
		margin: 0 0 16px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.step-num {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		border-radius: 50%;
		background: #333;
		color: #888;
		font-size: 11px;
		font-weight: 700;
		flex-shrink: 0;
	}

	.file-selected {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 16px;
		background: #1f1f1f;
		border-radius: 8px;
		margin-bottom: 12px;
	}

	.file-name {
		color: #ccc;
		font-size: 14px;
		font-weight: 500;
	}

	.file-size {
		color: #666;
		font-size: 12px;
	}

	.link-btn {
		background: none;
		border: none;
		color: #4fc3f7;
		cursor: pointer;
		font-size: 13px;
		margin-left: auto;
		padding: 4px 8px;
	}

	.link-btn:hover {
		text-decoration: underline;
	}

	.analyze-row {
		display: flex;
		gap: 12px;
	}

	.btn {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 10px 20px;
		border-radius: 8px;
		border: none;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-primary {
		background: #4fc3f7;
		color: #000;
	}

	.btn-primary:hover:not(:disabled) {
		background: #39b0e4;
	}

	.btn-secondary {
		background: #2a2a2a;
		color: #ccc;
		border: 1px solid #444;
	}

	.btn-secondary:hover:not(:disabled) {
		background: #333;
		border-color: #555;
	}

	.btn-record {
		background: #f44336;
		color: #fff;
	}

	.btn-record:hover {
		background: #d32f2f;
	}

	.hint {
		color: #666;
		font-size: 12px;
		margin: 8px 0 0;
	}

	.recording-area {
		padding: 4px 0;
	}

	.recording-active {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		background: rgba(244, 67, 54, 0.1);
		border-radius: 8px;
		border: 1px solid rgba(244, 67, 54, 0.3);
	}

	.rec-pulse {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: #f44336;
		animation: pulse 1s ease-in-out infinite;
		flex-shrink: 0;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.5; transform: scale(0.8); }
	}

	.rec-text {
		color: #f44336;
		font-size: 14px;
		font-weight: 500;
	}

	.recorded-preview {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.audio-player {
		width: 100%;
		height: 40px;
		border-radius: 6px;
	}

	.compare-row {
		display: flex;
		gap: 12px;
	}

	.reset-row {
		margin-top: 16px;
		display: flex;
		justify-content: center;
	}

	.spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(0,0,0,0.2);
		border-top-color: #000;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error-banner {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 16px;
		background: rgba(244,67,54,0.1);
		border: 1px solid rgba(244,67,54,0.3);
		border-radius: 8px;
		color: #f44336;
		font-size: 13px;
	}

	.dismiss {
		background: none;
		border: none;
		color: #f44336;
		cursor: pointer;
		font-size: 18px;
		margin-left: auto;
		padding: 0 4px;
	}
</style>
