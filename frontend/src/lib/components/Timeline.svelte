<script lang="ts">
	import type { ReferenceData } from '$lib/types';

	interface Props {
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
	}

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
	}: Props = $props();

	// --- Constants & Layout ---
	const CONFIG = {
		PX_PER_SEC: 180,
		LEFT_MARGIN: 60,
		MASTER_HEIGHT: 270,
		LANE_HEIGHT: 20,
		MAX_LANES: 4,
		WORD_Y_OFFSET: 10,
		PITCH: { top: 110, bottom: 200, color: '#4fc3f7' },
		VOL: { top: 210, bottom: 260, color: '#81c784' },
		COMP: { gap: 20, height: 200, pitchColor: '#ffb74d', volColor: '#ba68c8' }
	};

	let containerEl: HTMLDivElement | undefined = $state();
	let containerWidth = $state(0);
	let comparisonMode: 'stacked' | 'overlap' = $state('stacked');

	// --- Derived Calculations ---
	let maxDuration = $derived(Math.max(reference.duration, comparisonReference?.duration ?? 0));
	let contentWidth = $derived(maxDuration * CONFIG.PX_PER_SEC);
	let svgWidth = $derived(contentWidth + CONFIG.LEFT_MARGIN + 20);
	let svgHeight = $derived(
		comparisonReference && comparisonMode === 'stacked' 
			? CONFIG.MASTER_HEIGHT + CONFIG.COMP.gap + CONFIG.COMP.height 
			: CONFIG.MASTER_HEIGHT
	);

	let maxPitch = $derived(Math.max(1, ...reference.pitch, ...(comparisonReference?.pitch ?? [])));
	let maxRms = $derived(Math.max(0.01, ...reference.rms, ...(comparisonReference?.rms ?? [])));

	// Helper to convert time to X coordinate
	const timeToX = (t: number) => CONFIG.LEFT_MARGIN + t * CONFIG.PX_PER_SEC;

	// --- Drawing Helpers (Generators) ---
	function generatePoints(times: number[], values: number[], max: number, top: number, bottom: number) {
		if (times.length === 0) return "";
		return times.map((t, i) => {
			const x = timeToX(t);
			const norm = values[i] / max;
			const y = bottom - norm * (bottom - top);
			return `${x.toFixed(1)},${y.toFixed(1)}`;
		}).join(' ');
	}

	// --- Effects ---
	let raf: number;
	$effect(() => {
		if (!containerEl || !isPlaying) return;
		const updateScroll = () => {
			const cursorPos = timeToX(currentTime);
			const target = cursorPos - containerEl!.clientWidth * 0.3; // Keep cursor at 30% of view
			containerEl!.scrollLeft += (target - containerEl!.scrollLeft) * 0.1;
			raf = requestAnimationFrame(updateScroll);
		};
		raf = requestAnimationFrame(updateScroll);
		return () => cancelAnimationFrame(raf);
	});

	// --- Handlers ---
	function handleSvgClick(e: MouseEvent) {
		const svg = e.currentTarget as SVGSVGElement;
		const pt = svg.createSVGPoint();
		pt.x = e.clientX;
		pt.y = e.clientY;
		const localPt = pt.matrixTransform(svg.getScreenCTM()?.inverse());
		const seekTime = (localPt.x - CONFIG.LEFT_MARGIN) / CONFIG.PX_PER_SEC;
		onSeek(Math.max(0, Math.min(seekTime, reference.duration)));
	}

	// Dynamic lane assignment (Bug Fix: smarter collision detection)
	let wordLanes = $derived.by(() => {
		const lanes = new Array(CONFIG.MAX_LANES).fill(-1);
		return reference.words.map(word => {
			const startX = timeToX(word.start);
			const endX = timeToX(word.end) + 15; // Buffer
			let laneIdx = 0;
			for (let i = 0; i < CONFIG.MAX_LANES; i++) {
				if (lanes[i] < startX) {
					laneIdx = i;
					lanes[i] = endX;
					break;
				}
			}
			return laneIdx;
		});
	});
</script>

<!-- Snippet: Y-Axis Labels -->
{#snippet axisLabels(top, bottom, max, color, formatter)}
	{#each [0, 0.5, 1] as frac}
		{@const y = bottom - frac * (bottom - top)}
		<line x1={CONFIG.LEFT_MARGIN} y1={y} x2={svgWidth} y2={y} stroke="white" stroke-width="0.5" opacity="0.1" stroke-dasharray="4" />
		<text x={CONFIG.LEFT_MARGIN - 8} y={y + 3} fill={color} font-size="9" text-anchor="end" opacity="0.6">
			{formatter(max * frac)}
		</text>
	{/each}
{/snippet}

<div class="timeline-root" bind:offsetWidth={containerWidth}>
	<header class="toolbar">
		<div class="transport-controls">
			<button class="icon-btn main-action" onclick={isPlaying ? onPause : onPlay}>
				{#if isPlaying}<span class="i-pause"></span>{:else}<span class="i-play"></span>{/if}
			</button>
			<span class="timer">{Math.floor(currentTime)}s / {Math.floor(reference.duration)}s</span>
		</div>

		<div class="scrubber-track" 
			onclick={(e) => {
				const rect = e.currentTarget.getBoundingClientRect();
				onSeek(((e.clientX - rect.left) / rect.width) * reference.duration);
			}}>
			<div class="scrubber-fill" style="width: {(currentTime / reference.duration) * 100}%"></div>
		</div>

		<div class="audio-controls">
			<button class="icon-btn" onclick={onToggleMute}>
				<span class={masterMuted ? 'i-mute' : 'i-vol'}></span>
			</button>
			<input type="range" min="0" max="1" step="0.05" bind:value={masterVolume} oninput={() => onVolumeChange(masterVolume)} />
			
			{#if comparisonReference}
				<div class="toggle-group">
					<button class:active={comparisonMode === 'stacked'} onclick={() => comparisonMode = 'stacked'}>Stack</button>
					<button class:active={comparisonMode === 'overlap'} onclick={() => comparisonMode = 'overlap'}>Overlay</button>
				</div>
			{/if}
		</div>
	</header>

	<div class="scroll-container" bind:this={containerEl}>
		<div class="canvas-wrapper" style="width: {svgWidth}px; height: {svgHeight}px;">
			<svg {viewBox} width={svgWidth} height={svgHeight} onclick={handleSvgClick} class="timeline-svg">
				<!-- Background -->
				<rect width={svgWidth} height={svgHeight} fill="#0f0f0f" />

				<!-- Sections Backgrounds -->
				<rect x={CONFIG.LEFT_MARGIN} y={CONFIG.PITCH.top} width={contentWidth} height={CONFIG.PITCH.bottom - CONFIG.PITCH.top} fill="#4fc3f7" opacity="0.02" />
				<rect x={CONFIG.LEFT_MARGIN} y={CONFIG.VOL.top} width={contentWidth} height={CONFIG.VOL.bottom - CONFIG.VOL.top} fill="#81c784" opacity="0.02" />

				<!-- Y-Axis Guides -->
				{@render axisLabels(CONFIG.PITCH.top, CONFIG.PITCH.bottom, maxPitch, CONFIG.PITCH.color, (v) => v.toFixed(0))}
				{@render axisLabels(CONFIG.VOL.top, CONFIG.VOL.bottom, maxRms, CONFIG.VOL.color, (v) => v.toFixed(2))}

				<!-- Words Lane rendering -->
				{#each reference.words as word, i}
					{@const x = timeToX(word.start)}
					{@const isActive = currentTime >= word.start && currentTime <= word.end}
					<g class="word-group" opacity={isActive ? 1 : 0.6}>
						{#if isActive}
							<rect x={x - 4} y={CONFIG.WORD_Y_OFFSET + wordLanes[i] * CONFIG.LANE_HEIGHT} width={(word.end - word.start) * CONFIG.PX_PER_SEC + 8} height="16" fill={CONFIG.PITCH.color} opacity="0.2" rx="4" />
						{/if}
						<text 
							x={x} 
							y={CONFIG.WORD_Y_OFFSET + 12 + wordLanes[i] * CONFIG.LANE_HEIGHT} 
							fill={isActive ? CONFIG.PITCH.color : '#eee'} 
							font-size="12"
							font-weight={isActive ? "bold" : "normal"}
						>
							{word.word}
						</text>
					</g>
				{/each}

				<!-- Master Pitch Line -->
				<polyline 
					points={generatePoints(reference.times, reference.pitch, maxPitch, CONFIG.PITCH.top, CONFIG.PITCH.bottom)} 
					fill="none" stroke={CONFIG.PITCH.color} stroke-width="2" opacity="0.8"
				/>

				<!-- Master Volume Path -->
				{@const volPts = generatePoints(reference.times, reference.rms, maxRms, CONFIG.VOL.top, CONFIG.VOL.bottom)}
				{#if volPts}
					<path d="M {CONFIG.LEFT_MARGIN} {CONFIG.VOL.bottom} L {volPts} L {timeToX(reference.duration)} {CONFIG.VOL.bottom} Z" fill={CONFIG.VOL.color} opacity="0.1" />
					<polyline points={volPts} fill="none" stroke={CONFIG.VOL.color} stroke-width="1.5" opacity="0.7" />
				{/if}

				<!-- Comparison Logic -->
				{#if comparisonReference}
					{#if comparisonMode === 'overlap'}
						<polyline 
							points={generatePoints(comparisonReference.times, comparisonReference.pitch, maxPitch, CONFIG.PITCH.top, CONFIG.PITCH.bottom)} 
							fill="none" stroke={CONFIG.COMP.pitchColor} stroke-width="2" stroke-dasharray="4 2"
						/>
					{:else}
						<!-- Stacked Mode Offset Drawing -->
						{@const offset = CONFIG.MASTER_HEIGHT + CONFIG.COMP.gap}
						<g transform="translate(0, {offset})">
							<text x="10" y="20" fill={CONFIG.COMP.pitchColor} font-size="10" font-weight="bold">ATTEMPT</text>
							<polyline 
								points={generatePoints(comparisonReference.times, comparisonReference.pitch, maxPitch, 20, 100)} 
								fill="none" stroke={CONFIG.COMP.pitchColor} stroke-width="2"
							/>
							<polyline 
								points={generatePoints(comparisonReference.times, comparisonReference.rms, maxRms, 110, 180)} 
								fill="none" stroke={CONFIG.COMP.volColor} stroke-width="1.5"
							/>
						</g>
					{/if}
				{/if}

				<!-- Playhead Cursor -->
				{@const cursorX = timeToX(currentTime)}
				<g class="cursor">
					<line x1={cursorX} y1="0" x2={cursorX} y2={svgHeight} stroke="#fff" stroke-width="2" />
					<circle cx={cursorX} cy="0" r="4" fill="#fff" />
				</g>
			</svg>
		</div>
	</div>
</div>

<style>
	.timeline-root {
		--bg-dark: #121212;
		--bg-lighter: #1e1e1e;
		--accent: #4fc3f7;
		background: var(--bg-dark);
		border-radius: 8px;
		display: flex;
		flex-direction: column;
		user-select: none;
		border: 1px solid #333;
	}

	.toolbar {
		display: flex;
		align-items: center;
		padding: 8px 16px;
		gap: 16px;
		background: var(--bg-lighter);
		border-bottom: 1px solid #333;
	}

	.transport-controls {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.timer {
		font-family: monospace;
		font-size: 13px;
		color: #aaa;
		min-width: 80px;
	}

	.scrubber-track {
		flex: 1;
		height: 8px;
		background: #333;
		border-radius: 4px;
		position: relative;
		cursor: pointer;
	}

	.scrubber-fill {
		height: 100%;
		background: var(--accent);
		border-radius: 4px;
	}

	.audio-controls {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.scroll-container {
		overflow-x: auto;
		overflow-y: hidden;
		scrollbar-width: thin;
		scrollbar-color: #444 transparent;
	}

	.timeline-svg {
		display: block;
		cursor: crosshair;
	}

	.icon-btn {
		background: none;
		border: 1px solid #444;
		color: #ccc;
		border-radius: 4px;
		padding: 4px 8px;
		cursor: pointer;
	}

	.icon-btn:hover {
		border-color: var(--accent);
		color: #fff;
	}

	.toggle-group {
		display: flex;
		border: 1px solid #444;
		border-radius: 4px;
		overflow: hidden;
	}

	.toggle-group button {
		background: none;
		border: none;
		color: #888;
		padding: 4px 8px;
		font-size: 11px;
		cursor: pointer;
	}

	.toggle-group button.active {
		background: #444;
		color: #fff;
	}

	/* Simple pure CSS icons for the demo */
	.i-play::before { content: "▶"; }
	.i-pause::before { content: "II"; font-weight: bold; }
	.i-vol::before { content: "🔊"; }
	.i-mute::before { content: "🔇"; }
</style>
