<script lang="ts">
	import { api } from '$lib/api';
	import type { ComparisonResponse, ReferenceData, ScoreData, SentenceSegment } from '$lib/types';
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
	let selectedSentenceIds = $state<number[]>([]);

	let isRecording = $state(false);
	let recordedBlob = $state<Blob | null>(null);
	let recordedUrl = $state<string | null>(null);
	let mediaRecorder = $state<MediaRecorder | null>(null);
	let recordingStopTimer = $state<number | null>(null);

	let sentences = $derived(reference?.sentences ?? []);
	let selectedSentences = $derived.by(() => {
		if (!reference || selectedSentenceIds.length === 0) return [];
		const selected = new Set(selectedSentenceIds);
		return sentences.filter((sentence) => selected.has(sentence.id));
	});
	let practiceRange = $derived.by(() => {
		if (!reference || selectedSentences.length === 0) {
			return { start: 0, end: reference?.duration ?? 0 };
		}
		return {
			start: Math.min(...selectedSentences.map((sentence) => sentence.start)),
			end: Math.max(...selectedSentences.map((sentence) => sentence.end)),
		};
	});
	let activeReference = $derived.by(() => {
		if (!reference) return null;
		return sliceReference(reference, practiceRange.start, practiceRange.end);
	});

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

	function sliceReference(data: ReferenceData, start: number, end: number): ReferenceData {
		const duration = Math.max(0.1, end - start);
		const inRange = (time: number) => time >= start && time <= end;
		const frameIndexes = data.times
			.map((time, index) => ({ time, index }))
			.filter(({ time }) => inRange(time));
		const fallbackIndex = data.times.reduce((bestIndex, time, index) => {
			return Math.abs(time - start) < Math.abs(data.times[bestIndex] - start) ? index : bestIndex;
		}, 0);
		const indexes = frameIndexes.length > 0 ? frameIndexes.map(({ index }) => index) : [fallbackIndex];

		return {
			...data,
			words: data.words
				.filter((word) => word.end >= start && word.start <= end)
				.map((word) => ({
					...word,
					start: Math.max(0, word.start - start),
					end: Math.min(duration, word.end - start),
				})),
			sentences: data.sentences
				?.filter((sentence) => sentence.end >= start && sentence.start <= end)
				.map((sentence) => ({
					...sentence,
					start: Math.max(0, sentence.start - start),
					end: Math.min(duration, sentence.end - start),
				})),
			times: indexes.map((index) => Math.max(0, data.times[index] - start)),
			rms: indexes.map((index) => data.rms[index]),
			pitch: indexes.map((index) => data.pitch[index]),
			pause_mask: indexes.map((index) => data.pause_mask[index]),
			pause_regions: data.pause_regions
				.filter((region) => region.end >= start && region.start <= end)
				.map((region) => ({
					start: Math.max(0, region.start - start),
					end: Math.min(duration, region.end - start),
				})),
			cps: indexes.map((index) => data.cps[index]),
			duration,
		};
	}

	function clearAttempt() {
		recordedBlob = null;
		if (recordedUrl) URL.revokeObjectURL(recordedUrl);
		recordedUrl = null;
		score = null;
		attemptReference = null;
	}

	function setPracticeSelection(ids: number[]) {
		pause();
		selectedSentenceIds = [...new Set(ids)].sort((a, b) => a - b);
		clearAttempt();
		seek(0);
	}

	function selectSentence(id: number) {
		setPracticeSelection([id]);
	}

	function toggleSentence(sentence: SentenceSegment) {
		if (selectedSentenceIds.includes(sentence.id)) {
			setPracticeSelection(selectedSentenceIds.filter((id) => id !== sentence.id));
			return;
		}
		setPracticeSelection([...selectedSentenceIds, sentence.id]);
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
    	if (isRecording) {
    		stopRecording();
    	}
    
    	isPlaying = false;
    	currentTime = activeReference?.duration ?? 0;
    
    	if (rafId) {
    		cancelAnimationFrame(rafId);
    		rafId = 0;
    	}
    };
		audioEl = el;
	}

	function startPlaybackLoop() {
		if (rafId) cancelAnimationFrame(rafId);
		function tick() {
			if (audioEl) {
				if (audioEl.currentTime >= practiceRange.end) {
					pause();
					currentTime = activeReference?.duration ?? 0;
					return;
				}
				currentTime = Math.max(0, audioEl.currentTime - practiceRange.start);
			}
			if (audioEl && !audioEl.paused) rafId = requestAnimationFrame(tick);
		}
		rafId = requestAnimationFrame(tick);
	}

	async function play() {
		if (!audioEl) return;
		if (audioEl.currentTime < practiceRange.start || audioEl.currentTime >= practiceRange.end) {
			audioEl.currentTime = practiceRange.start;
			currentTime = 0;
		}
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
			audioEl.currentTime = practiceRange.start + t;
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
			selectedSentenceIds = res.data.sentences?.[0] ? [res.data.sentences[0].id] : [];
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
		if (!activeReference) return;
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
					autoGainControl: true,
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
      	if (
      		activeRecorder.state === 'recording' &&
      		audioEl &&
      		!audioEl.ended
      	) {
      		stopRecording();
      	}
      }, (activeReference.duration + 1) * 1000);
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
		if (!masterFile || !recordedBlob || !activeReference) return;
		loading = true;
		error = null;
		try {
			const formData = new FormData();
			formData.append('master_audio', masterFile);
			formData.append('master_start', String(practiceRange.start));
			formData.append('master_end', String(practiceRange.end));
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
		{#if reference && activeReference}
			<section class="section">
				<h2 class="section-label">
					<span class="step-num">2</span>
					Speaking Blueprint
				</h2>
				{#if sentences.length > 0}
					<div class="practice-picker">
						<div class="picker-row">
							<label class="picker-label" for="sentence-select">Practice sentence</label>
							<select
								id="sentence-select"
								class="sentence-select"
								value={selectedSentenceIds[0] ?? ''}
								onchange={(e) => selectSentence(Number((e.currentTarget as HTMLSelectElement).value))}
							>
								{#each sentences as sentence}
									<option value={sentence.id}>
										{sentence.index + 1}. {sentence.text}
									</option>
								{/each}
							</select>
						</div>
						<div class="sentence-checklist" aria-label="Select multiple sentences">
							{#each sentences as sentence}
								<label class="sentence-chip" class:checked={selectedSentenceIds.includes(sentence.id)}>
									<input
										type="checkbox"
										checked={selectedSentenceIds.includes(sentence.id)}
										onchange={() => toggleSentence(sentence)}
									/>
									<span>{sentence.index + 1}</span>
								</label>
							{/each}
						</div>
						<p class="hint">
							Practicing {selectedSentences.length || sentences.length} sentence{(selectedSentences.length || sentences.length) === 1 ? '' : 's'}
							({practiceRange.start.toFixed(1)}s-{practiceRange.end.toFixed(1)}s)
						</p>
					</div>
				{/if}
				<Timeline
					reference={activeReference}
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
						<p class="hint">Max {activeReference.duration.toFixed(0)} seconds</p>
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

	.practice-picker {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin-bottom: 16px;
		padding: 12px;
		background: #1f1f1f;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
	}

	.picker-row {
		display: grid;
		grid-template-columns: 140px 1fr;
		gap: 12px;
		align-items: center;
	}

	.picker-label {
		color: #888;
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.sentence-select {
		width: 100%;
		min-width: 0;
		background: #151515;
		border: 1px solid #3a3a3a;
		border-radius: 7px;
		color: #ddd;
		font-size: 13px;
		padding: 8px 10px;
	}

	.sentence-checklist {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.sentence-chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		min-width: 38px;
		height: 30px;
		justify-content: center;
		background: #151515;
		border: 1px solid #3a3a3a;
		border-radius: 7px;
		color: #888;
		cursor: pointer;
		font-size: 12px;
		font-weight: 600;
		padding: 0 8px;
	}

	.sentence-chip.checked {
		border-color: #4fc3f7;
		color: #e0e0e0;
		background: rgba(79, 195, 247, 0.12);
	}

	.sentence-chip input {
		margin: 0;
		accent-color: #4fc3f7;
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
