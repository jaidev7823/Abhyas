<script lang="ts">
	import type { ReferenceData } from '$lib/types';

	let {
		reference,
		comparisonReference = null,
		currentTime,
		isPlaying,
		masterMuted = false,
		masterVolume = 1,
		onPlay,
		onPause,
		onSeek,
		onToggleMute = () => {},
		onVolumeChange = () => {},
	}: {
		reference: ReferenceData;
		comparisonReference?: ReferenceData | null;
		currentTime: number;
		isPlaying: boolean;
		masterMuted?: boolean;
		masterVolume?: number;
		onPlay: () => void;
		onPause: () => void;
		onSeek: (t: number) => void;
		onToggleMute?: () => void;
		onVolumeChange?: (volume: number) => void;
	} = $props();

	const PX_PER_SEC = 180;
	const LEFT_MARGIN = 55;
	const MASTER_HEIGHT = 270;
	const WORD_HEIGHT = 48;
	const PITCH_TOP = 52;
	const PITCH_BOTTOM = 158;
	const VOL_TOP = 166;
	const VOL_BOTTOM = 248;
	const COMP_GAP = 22;
	const COMP_TOP = MASTER_HEIGHT + COMP_GAP;
	const COMP_HEIGHT = 210;
	const COMP_LABEL_HEIGHT = 30;
	const COMP_PITCH_TOP = COMP_TOP + COMP_LABEL_HEIGHT;
	const COMP_PITCH_BOTTOM = COMP_TOP + 112;
	const COMP_VOL_TOP = COMP_TOP + 120;
	const COMP_VOL_BOTTOM = COMP_TOP + 190;

	let containerEl: HTMLDivElement | undefined = $state();
	let containerWidth = $state(0);
	let comparisonMode: 'stacked' | 'overlap' = $state('stacked');

	$effect(() => {
		if (!containerEl) return;
		const ro = new ResizeObserver((entries) => {
			containerWidth = entries[0].contentRect.width;
		});
		ro.observe(containerEl);
		return () => ro.disconnect();
	});

	let maxDuration = $derived(Math.max(reference.duration, comparisonReference?.duration ?? 0));
	let contentWidth = $derived(Math.max(500, maxDuration * PX_PER_SEC));
	let svgWidth = $derived(contentWidth + LEFT_MARGIN);
	let renderWidth = $derived(Math.max(containerWidth || 0, svgWidth));
	let svgHeight = $derived(comparisonReference && comparisonMode === 'stacked' ? COMP_TOP + COMP_HEIGHT : MASTER_HEIGHT);

	let currentWordIdx = $derived(
		reference.words.findIndex((w) => currentTime >= w.start && currentTime < w.end)
	);

	let maxRms = $derived(Math.max(...reference.rms, ...(comparisonReference?.rms ?? [0])));
	let maxPitch = $derived(Math.max(...reference.pitch, ...(comparisonReference?.pitch ?? [0])));

	let pitchPoints = $derived.by(() =>
		reference.times
			.map((t, i) => {
				const x = LEFT_MARGIN + t * PX_PER_SEC;
				const p = reference.pitch[i];
				const norm = maxPitch > 0 ? p / maxPitch : 0;
				const y = PITCH_BOTTOM - norm * (PITCH_BOTTOM - PITCH_TOP);
				return `${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ')
	);

	let volLinePoints = $derived.by(() =>
		reference.times
			.map((t, i) => {
				const x = LEFT_MARGIN + t * PX_PER_SEC;
				const r = reference.rms[i];
				const norm = maxRms > 0 ? r / maxRms : 0;
				const y = VOL_BOTTOM - norm * (VOL_BOTTOM - VOL_TOP);
				return `${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ')
	);

	let volFill = $derived.by(() => {
		if (reference.times.length === 0) return '';
		const firstX = LEFT_MARGIN;
		const lastX = LEFT_MARGIN + reference.duration * PX_PER_SEC;
		return `M${firstX.toFixed(1)},${VOL_BOTTOM}L${volLinePoints}L${lastX.toFixed(1)},${VOL_BOTTOM}Z`;
	});

	let cursorX = $derived(LEFT_MARGIN + currentTime * PX_PER_SEC);

	let comparisonPitchPoints = $derived.by(() => {
		if (!comparisonReference) return '';
		return comparisonReference.times
			.map((t, i) => {
				const x = LEFT_MARGIN + t * PX_PER_SEC;
				const p = comparisonReference.pitch[i];
				const norm = maxPitch > 0 ? p / maxPitch : 0;
				const y = COMP_PITCH_BOTTOM - norm * (COMP_PITCH_BOTTOM - COMP_PITCH_TOP);
				return `${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ');
	});

	let comparisonVolLinePoints = $derived.by(() => {
		if (!comparisonReference) return '';
		return comparisonReference.times
			.map((t, i) => {
				const x = LEFT_MARGIN + t * PX_PER_SEC;
				const r = comparisonReference.rms[i];
				const norm = maxRms > 0 ? r / maxRms : 0;
				const y = COMP_VOL_BOTTOM - norm * (COMP_VOL_BOTTOM - COMP_VOL_TOP);
				return `${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ');
	});

	let comparisonVolFill = $derived.by(() => {
		if (!comparisonReference || comparisonReference.times.length === 0) return '';
		const firstX = LEFT_MARGIN;
		const lastX = LEFT_MARGIN + comparisonReference.duration * PX_PER_SEC;
		return `M${firstX.toFixed(1)},${COMP_VOL_BOTTOM}L${comparisonVolLinePoints}L${lastX.toFixed(1)},${COMP_VOL_BOTTOM}Z`;
	});

	let overlayPitchPoints = $derived.by(() => {
		if (!comparisonReference) return '';
		return comparisonReference.times
			.map((t, i) => {
				const x = LEFT_MARGIN + t * PX_PER_SEC;
				const p = comparisonReference.pitch[i];
				const norm = maxPitch > 0 ? p / maxPitch : 0;
				const y = PITCH_BOTTOM - norm * (PITCH_BOTTOM - PITCH_TOP);
				return `${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ');
	});

	let overlayVolLinePoints = $derived.by(() => {
		if (!comparisonReference) return '';
		return comparisonReference.times
			.map((t, i) => {
				const x = LEFT_MARGIN + t * PX_PER_SEC;
				const r = comparisonReference.rms[i];
				const norm = maxRms > 0 ? r / maxRms : 0;
				const y = VOL_BOTTOM - norm * (VOL_BOTTOM - VOL_TOP);
				return `${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ');
	});

	let currentWord = $derived(currentWordIdx >= 0 ? reference.words[currentWordIdx] : null);

	function handleSvgClick(e: MouseEvent) {
		const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
		const xRatio = (e.clientX - rect.left) / rect.width;
		const time = (xRatio * svgWidth - LEFT_MARGIN) / PX_PER_SEC;
		onSeek(Math.max(0, Math.min(time, reference.duration)));
	}

	function formatTime(s: number): string {
		const m = Math.floor(s / 60);
		const sec = Math.floor(s % 60);
		return `${m}:${sec.toString().padStart(2, '0')}`;
	}

	$effect(() => {
		if (!currentWord || !containerEl) return;
		const scrollEl = containerEl;
		const wordCenter = ((LEFT_MARGIN + currentWord.start * PX_PER_SEC) / svgWidth) * scrollEl.scrollWidth;
		const half = scrollEl.clientWidth / 2;
		if (wordCenter > half) {
			scrollEl.scrollLeft = wordCenter - half;
		}
	});
</script>

<div class="timeline-container">
	<div class="timeline-toolbar">
		<button class="play-btn" onclick={isPlaying ? onPause : onPlay}>
			<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
				{#if isPlaying}
					<rect x="6" y="4" width="4" height="16" />
					<rect x="14" y="4" width="4" height="16" />
				{:else}
					<polygon points="6,4 20,12 6,20" />
				{/if}
			</svg>
		</button>
		<span class="time-display">{formatTime(currentTime)} / {formatTime(reference.duration)}</span>
		<div class="progress-bar" role="slider" tabindex="0" aria-valuenow={currentTime}
			onclick={(e) => {
				const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
				const ratio = (e.clientX - rect.left) / rect.width;
				onSeek(ratio * reference.duration);
			}}
			onkeydown={(e) => {
				if (e.key === 'ArrowRight') onSeek(Math.min(currentTime + 1, reference.duration));
				if (e.key === 'ArrowLeft') onSeek(Math.max(currentTime - 1, 0));
			}}
		>
			<div class="progress-fill" style="width: {Math.min(100, (currentTime / reference.duration) * 100)}%"></div>
		</div>
		<button
			class="mute-btn"
			type="button"
			aria-label={masterMuted ? 'Unmute master audio' : 'Mute master audio'}
			aria-pressed={masterMuted}
			onclick={onToggleMute}
		>
			<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
				{#if masterMuted}
					<line x1="18" y1="9" x2="22" y2="13" />
					<line x1="22" y1="9" x2="18" y2="13" />
				{:else}
					<path d="M15 9.5a4 4 0 0 1 0 5" />
					<path d="M18 7a8 8 0 0 1 0 10" />
				{/if}
			</svg>
		</button>
		<input
			class="volume-slider"
			type="range"
			min="0"
			max="1"
			step="0.01"
			value={masterVolume}
			aria-label="Master audio volume"
			oninput={(e) => onVolumeChange(Number((e.currentTarget as HTMLInputElement).value))}
		/>
		{#if comparisonReference}
			<div class="compare-toggle" aria-label="Comparison view">
				<button
					type="button"
					class:active={comparisonMode === 'stacked'}
					onclick={() => comparisonMode = 'stacked'}
				>
					Stack
				</button>
				<button
					type="button"
					class:active={comparisonMode === 'overlap'}
					onclick={() => comparisonMode = 'overlap'}
				>
					Overlap
				</button>
			</div>
		{/if}
	</div>

	<div class="timeline-scroll" bind:this={containerEl}>
		<div class="timeline-inner" style="width: {renderWidth}px; height: {svgHeight}px;">
			<svg
				viewBox="0 0 {svgWidth} {svgHeight}"
				style="width: 100%; height: 100%;"
				role="button"
				aria-label="Seek master timeline"
				tabindex="0"
				onclick={handleSvgClick}
				onkeydown={(e) => {
					if (e.key === 'ArrowRight') onSeek(Math.min(currentTime + 1, reference.duration));
					if (e.key === 'ArrowLeft') onSeek(Math.max(currentTime - 1, 0));
				}}
			>
				<rect x="0" y="0" width={svgWidth} height={svgHeight} fill="#131313" rx="8" />

				<rect x={LEFT_MARGIN} y="0" width={contentWidth} height={WORD_HEIGHT} fill="rgba(255,255,255,0.02)" />
				<rect x={LEFT_MARGIN} y={PITCH_TOP} width={contentWidth} height={PITCH_BOTTOM - PITCH_TOP} fill="rgba(79,195,247,0.03)" />
				<rect x={LEFT_MARGIN} y={VOL_TOP} width={contentWidth} height={VOL_BOTTOM - VOL_TOP} fill="rgba(129,199,132,0.03)" />

				{#each [0, 0.25, 0.5, 0.75, 1] as frac}
					<line
						x1={LEFT_MARGIN}
						y1={PITCH_BOTTOM - frac * (PITCH_BOTTOM - PITCH_TOP)}
						x2={LEFT_MARGIN + contentWidth}
						y2={PITCH_BOTTOM - frac * (PITCH_BOTTOM - PITCH_TOP)}
						stroke="rgba(255,255,255,0.06)" stroke-width="1" stroke-dasharray="4,4"
					/>
				{/each}

				{#each [0, 0.33, 0.66, 1] as frac}
					<line
						x1={LEFT_MARGIN}
						y1={VOL_BOTTOM - frac * (VOL_BOTTOM - VOL_TOP)}
						x2={LEFT_MARGIN + contentWidth}
						y2={VOL_BOTTOM - frac * (VOL_BOTTOM - VOL_TOP)}
						stroke="rgba(255,255,255,0.06)" stroke-width="1" stroke-dasharray="4,4"
					/>
				{/each}

				<line x1={LEFT_MARGIN} y1={PITCH_TOP} x2={LEFT_MARGIN + contentWidth} y2={PITCH_TOP} stroke="rgba(255,255,255,0.08)" stroke-width="1" />
				<line x1={LEFT_MARGIN} y1={VOL_TOP} x2={LEFT_MARGIN + contentWidth} y2={VOL_TOP} stroke="rgba(255,255,255,0.08)" stroke-width="1" />

				{#each reference.pause_regions as region}
					<rect
						x={LEFT_MARGIN + region.start * PX_PER_SEC}
						y="0"
						width={Math.max(2, (region.end - region.start) * PX_PER_SEC)}
						height={MASTER_HEIGHT}
						fill="rgba(244,67,54,0.08)"
						rx="2"
					/>
				{/each}

        {#each reference.words as word, i}
        	{@const wX = LEFT_MARGIN + word.start * PX_PER_SEC}
        	{@const wEnd = LEFT_MARGIN + word.end * PX_PER_SEC}
        	{@const wW = Math.max(20, (word.end - word.start) * PX_PER_SEC)}
        	
        	{#if i === currentWordIdx}
        		<rect x={wX} y="4" width={wW} height={WORD_HEIGHT - 8} fill="rgba(79,195,247,0.2)" rx="4" />
        	{/if}
        
        	<text
        		x={wEnd - 6}
        		y={WORD_HEIGHT / 2 + 1}
        		fill={i === currentWordIdx ? '#4fc3f7' : '#999'}
        		font-size="13"
        		font-weight={i === currentWordIdx ? '700' : '400'}
        		font-family="system-ui, sans-serif"
        		dominant-baseline="middle"
        		text-anchor="end"
        	>
        		{word.word}
        	</text>
        {/each}		
        <text x="8" y={PITCH_TOP + (PITCH_BOTTOM - PITCH_TOP) / 2 + 4}
					fill="#4fc3f7" font-size="10" font-family="system-ui, sans-serif"
					transform="rotate(-90, 8, {PITCH_TOP + (PITCH_BOTTOM - PITCH_TOP) / 2 + 4})"
					text-anchor="middle" opacity="0.7">PITCH</text>

				{#if pitchPoints}
					<polyline points={pitchPoints} fill="none" stroke="#4fc3f7" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" opacity="0.9" />
				{/if}

				<text x="8" y={VOL_TOP + (VOL_BOTTOM - VOL_TOP) / 2 + 4}
					fill="#81c784" font-size="10" font-family="system-ui, sans-serif"
					transform="rotate(-90, 8, {VOL_TOP + (VOL_BOTTOM - VOL_TOP) / 2 + 4})"
					text-anchor="middle" opacity="0.7">VOLUME</text>

				{#if volFill}
					<path d={volFill} fill="rgba(129,199,132,0.15)" />
					<polyline points={volLinePoints} fill="none" stroke="#81c784" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" opacity="0.8" />
				{/if}

				{#if comparisonReference && comparisonMode === 'overlap'}
					<g opacity="0.95">
						<rect x={LEFT_MARGIN + 10} y="9" width="164" height="24" fill="rgba(19,19,19,0.8)" rx="5" />
						<line x1={LEFT_MARGIN + 20} y1="21" x2={LEFT_MARGIN + 42} y2="21" stroke="#4fc3f7" stroke-width="2" />
						<text x={LEFT_MARGIN + 48} y="24" fill="#aaa" font-size="10" font-family="system-ui, sans-serif">master</text>
						<line x1={LEFT_MARGIN + 88} y1="21" x2={LEFT_MARGIN + 110} y2="21" stroke="#ffb74d" stroke-width="2" stroke-dasharray="5,4" />
						<text x={LEFT_MARGIN + 116} y="24" fill="#aaa" font-size="10" font-family="system-ui, sans-serif">attempt</text>
					</g>

					{#if overlayPitchPoints}
						<polyline points={overlayPitchPoints} fill="none" stroke="#ffb74d" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="5,4" opacity="0.95" />
					{/if}

					{#if overlayVolLinePoints}
						<polyline points={overlayVolLinePoints} fill="none" stroke="#ba68c8" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="5,4" opacity="0.9" />
					{/if}
				{/if}

				{#each Array.from({ length: Math.ceil(maxDuration / 2) + 1 }, (_, i) => i * 2) as sec}
					{@const tx = LEFT_MARGIN + sec * PX_PER_SEC}
					<line x1={tx} y1="0" x2={tx} y2={svgHeight} stroke="rgba(255,255,255,0.03)" stroke-width="1" />
					<text x={tx} y={MASTER_HEIGHT - 2} fill="#555" font-size="9" font-family="system-ui, sans-serif" text-anchor="middle">{sec}s</text>
				{/each}

				{#if comparisonReference && comparisonMode === 'stacked'}
					<line x1="0" y1={MASTER_HEIGHT + 10} x2={svgWidth} y2={MASTER_HEIGHT + 10} stroke="rgba(255,255,255,0.08)" stroke-width="1" />
					<rect x={LEFT_MARGIN} y={COMP_TOP} width={contentWidth} height={COMP_HEIGHT - 20} fill="rgba(255,255,255,0.018)" rx="6" />
					<text x="8" y={COMP_TOP + 18} fill="#aaa" font-size="10" font-family="system-ui, sans-serif" opacity="0.75">ATTEMPT</text>
					<text x="8" y={COMP_PITCH_TOP + (COMP_PITCH_BOTTOM - COMP_PITCH_TOP) / 2 + 4}
						fill="#ffb74d" font-size="10" font-family="system-ui, sans-serif"
						transform="rotate(-90, 8, {COMP_PITCH_TOP + (COMP_PITCH_BOTTOM - COMP_PITCH_TOP) / 2 + 4})"
						text-anchor="middle" opacity="0.75">PITCH</text>
					<text x="8" y={COMP_VOL_TOP + (COMP_VOL_BOTTOM - COMP_VOL_TOP) / 2 + 4}
						fill="#ba68c8" font-size="10" font-family="system-ui, sans-serif"
						transform="rotate(-90, 8, {COMP_VOL_TOP + (COMP_VOL_BOTTOM - COMP_VOL_TOP) / 2 + 4})"
						text-anchor="middle" opacity="0.75">VOLUME</text>

					<rect x={LEFT_MARGIN} y={COMP_PITCH_TOP} width={contentWidth} height={COMP_PITCH_BOTTOM - COMP_PITCH_TOP} fill="rgba(255,183,77,0.035)" />
					<rect x={LEFT_MARGIN} y={COMP_VOL_TOP} width={contentWidth} height={COMP_VOL_BOTTOM - COMP_VOL_TOP} fill="rgba(186,104,200,0.035)" />

					{#each comparisonReference.pause_regions as region}
						<rect
							x={LEFT_MARGIN + region.start * PX_PER_SEC}
							y={COMP_TOP}
							width={Math.max(2, (region.end - region.start) * PX_PER_SEC)}
							height={COMP_HEIGHT - 20}
							fill="rgba(244,67,54,0.07)"
							rx="2"
						/>
					{/each}

					{#if comparisonPitchPoints}
						<polyline points={comparisonPitchPoints} fill="none" stroke="#ffb74d" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" opacity="0.9" />
					{/if}

					{#if comparisonVolFill}
						<path d={comparisonVolFill} fill="rgba(186,104,200,0.15)" />
						<polyline points={comparisonVolLinePoints} fill="none" stroke="#ba68c8" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" opacity="0.85" />
					{/if}

					<line x1={LEFT_MARGIN} y1={COMP_PITCH_TOP} x2={LEFT_MARGIN + contentWidth} y2={COMP_PITCH_TOP} stroke="rgba(255,255,255,0.08)" stroke-width="1" />
					<line x1={LEFT_MARGIN} y1={COMP_VOL_TOP} x2={LEFT_MARGIN + contentWidth} y2={COMP_VOL_TOP} stroke="rgba(255,255,255,0.08)" stroke-width="1" />
				{/if}

				<line x1={cursorX} y1="0" x2={cursorX} y2={svgHeight} stroke="#fff" stroke-width="2" stroke-linecap="round" opacity="0.85" />
				<circle cx={cursorX} cy="0" r="4" fill="#fff" opacity="0.85" />
			</svg>
		</div>
	</div>
</div>

<style>
	.timeline-container {
		background: #131313;
		border-radius: 12px;
		overflow: hidden;
	}
	.timeline-toolbar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 16px;
		background: #1a1a1a;
		border-bottom: 1px solid #222;
	}
	.play-btn {
		background: none;
		border: 1px solid #444;
		border-radius: 50%;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		color: #ccc;
		padding: 0;
		transition: all 0.15s;
		flex-shrink: 0;
	}
	.play-btn:hover {
		border-color: #4fc3f7;
		color: #4fc3f7;
		background: rgba(79, 195, 247, 0.1);
	}
	.time-display {
		color: #888;
		font-size: 13px;
		font-family: monospace;
		flex-shrink: 0;
		min-width: 90px;
	}
	.progress-bar {
		flex: 1;
		height: 6px;
		background: #333;
		border-radius: 3px;
		cursor: pointer;
		position: relative;
	}
	.progress-fill {
		height: 100%;
		background: #4fc3f7;
		border-radius: 3px;
		transition: width 0.1s linear;
	}
	.mute-btn {
		background: none;
		border: 1px solid #444;
		border-radius: 6px;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #aaa;
		cursor: pointer;
		padding: 0;
		flex-shrink: 0;
	}
	.mute-btn:hover {
		border-color: #4fc3f7;
		color: #4fc3f7;
		background: rgba(79, 195, 247, 0.08);
	}
	.mute-btn[aria-pressed="true"] {
		color: #f44336;
		border-color: rgba(244, 67, 54, 0.5);
	}
	.volume-slider {
		width: 96px;
		accent-color: #4fc3f7;
		flex-shrink: 0;
	}
	.compare-toggle {
		display: inline-flex;
		border: 1px solid #3a3a3a;
		border-radius: 7px;
		overflow: hidden;
		flex-shrink: 0;
	}
	.compare-toggle button {
		background: #202020;
		border: none;
		color: #888;
		cursor: pointer;
		font-size: 12px;
		font-weight: 600;
		padding: 7px 10px;
	}
	.compare-toggle button + button {
		border-left: 1px solid #3a3a3a;
	}
	.compare-toggle button.active {
		background: #333;
		color: #fff;
	}
	.timeline-scroll {
		overflow-x: auto;
		overflow-y: hidden;
		cursor: crosshair;
	}
	.timeline-scroll::-webkit-scrollbar {
		height: 6px;
	}
	.timeline-scroll::-webkit-scrollbar-track {
		background: #1a1a1a;
	}
	.timeline-scroll::-webkit-scrollbar-thumb {
		background: #444;
		border-radius: 3px;
	}
	.timeline-scroll::-webkit-scrollbar-thumb:hover {
		background: #555;
	}
	.timeline-inner {
		flex-shrink: 0;
	}
</style>
