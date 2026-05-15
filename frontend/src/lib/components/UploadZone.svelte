<script lang="ts">
	let { onFile }: { onFile: (f: File) => void } = $props();

	let dragging = $state(false);
	let inputEl: HTMLInputElement | undefined = $state();

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragging = false;
		const file = e.dataTransfer?.files?.[0];
		if (file) onFile(file);
	}

	function handleChange(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (file) onFile(file);
	}
</script>

<div
	class="upload-zone"
	class:dragging={dragging}
	role="button"
	tabindex="0"
	ondragover={(e) => { e.preventDefault(); dragging = true; }}
	ondragleave={() => { dragging = false; }}
	ondrop={handleDrop}
	onclick={() => inputEl?.click()}
	onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputEl?.click(); }}
>
	<input
		type="file"
		accept="audio/*,.wav,.mp3,.m4a,.ogg,.flac"
		class="hidden"
		bind:this={inputEl}
		onchange={handleChange}
	/>
	<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
		<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
		<polyline points="17 8 12 3 7 8" />
		<line x1="12" y1="3" x2="12" y2="15" />
	</svg>
	<p class="upload-text">Drop audio file here or click to browse</p>
	<p class="upload-hint">WAV, MP3, M4A, OGG, FLAC</p>
</div>

<style>
	.upload-zone {
		border: 2px dashed #444;
		border-radius: 12px;
		padding: 32px;
		text-align: center;
		cursor: pointer;
		transition: all 0.2s;
		background: #1a1a1a;
	}
	.upload-zone:hover,
	.upload-zone.dragging {
		border-color: #4fc3f7;
		background: #1e2a33;
	}
	.hidden {
		display: none;
	}
	.upload-text {
		margin: 12px 0 4px;
		color: #ccc;
		font-size: 14px;
	}
	.upload-hint {
		margin: 0;
		color: #666;
		font-size: 12px;
	}
</style>
