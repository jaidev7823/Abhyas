<script lang="ts">
	import type { ReferenceData } from '$lib/types';

	let {
		reference,
		currentTime,
		isPlaying,
		onPlay,
		onPause,
		onSeek,
	}: {
		reference: ReferenceData;
		currentTime: number;
		isPlaying: boolean;
		onPlay: () => void;
		onPause: () => void;
		onSeek: (t: number) => void;
	} = $props();

	const PX_PER_SEC = 180;
	const LEFT_MARGIN = 55;
	const SVG_HEIGHT = 270;
	const WORD_HEIGHT = 48;
	const PITCH_TOP = 52;
	const PITCH_BOTTOM = 158;
	const VOL_TOP = 166;
	const VOL_BOTTOM = 248;

	let containerEl: HTMLDivElement | undefined = $state();
	let containerWidth = $state(0);

	$effect(() => {
		if (!containerEl) return;
		const ro = new ResizeObserver((entries) => {
			containerWidth = entries[0].contentRect.width;
		});
		ro.observe(containerEl);
		return () => ro.disconnect();
	});

	let contentWidth = $derived(Math.max(500, reference.duration * PX_PER_SEC));
	let svgWidth = $derived(contentWidth + LEFT_MARGIN);
	let renderWidth = $derived(Math.max(containerWidth || 0, svgWidth));

	let currentWordIdx = $derived(
		reference.words.findIndex((w) => currentTime >= w.start && currentTime < w.end)
	);

	let maxRms = $derived(Math.max(...reference.rms));
	let maxPitch = $derived(Math.max(...reference.pitch));

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
			<div class="progress-fill" style="width: {(currentTime / reference.duration) * 100}%"></div>
		</div>
	</div>

	<div class="timeline-scroll" bind:this={containerEl}>
		<div class="timeline-inner" style="width: {renderWidth}px; height: {SVG_HEIGHT}px;">
			<svg
				viewBox="0 0 {svgWidth} {SVG_HEIGHT}"
				style="width: 100%; height: 100%;"
				role="img"
				tabindex="0"
				onclick={handleSvgClick}
				onkeydown={(e) => {
					if (e.key === 'ArrowRight') onSeek(Math.min(currentTime + 1, reference.duration));
					if (e.key === 'ArrowLeft') onSeek(Math.max(currentTime - 1, 0));
				}}
			>
				<rect x="0" y="0" width={svgWidth} height={SVG_HEIGHT} fill="#131313" rx="8" />

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
						height={SVG_HEIGHT}
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

				{#each Array.from({ length: Math.ceil(reference.duration / 2) + 1 }, (_, i) => i * 2) as sec}
					{@const tx = LEFT_MARGIN + sec * PX_PER_SEC}
					<line x1={tx} y1="0" x2={tx} y2={SVG_HEIGHT} stroke="rgba(255,255,255,0.03)" stroke-width="1" />
					<text x={tx} y={SVG_HEIGHT - 2} fill="#555" font-size="9" font-family="system-ui, sans-serif" text-anchor="middle">{sec}s</text>
				{/each}

				<line x1={cursorX} y1="0" x2={cursorX} y2={SVG_HEIGHT} stroke="#fff" stroke-width="2" stroke-linecap="round" opacity="0.85" />
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
