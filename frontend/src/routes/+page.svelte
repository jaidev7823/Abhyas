<script lang="ts">
	import { api } from '$lib/api';

	let masterAudio: File | null = null;
	let userAudio: File | null = null;

	let loading = false;

	let reference: any = null;
	let compare: any = null;

	async function generateReference() {
		if (!masterAudio) return;

		loading = true;

		const formData = new FormData();

		formData.append('audio', masterAudio);

		const response = await api.post(
			'/shadow/analyze-master',
			formData,
			{
				headers: {
					'Content-Type': 'multipart/form-data'
				}
			}
		);

		reference = response.data;

		loading = false;
	}

	async function compareAttempt() {
		if (!masterAudio || !userAudio) return;

		loading = true;

		const formData = new FormData();

		formData.append('master_audio', masterAudio);
		formData.append('user_audio', userAudio);

		const response = await api.post(
			'/shadow/compare-attempt',
			formData,
			{
				headers: {
					'Content-Type': 'multipart/form-data'
				}
			}
		);

		compare = response.data;

		loading = false;
	}
</script>

<div class="container">
	<h1>Shadowing Coach</h1>

	<div class="card">
		<h2>1. Upload Master Audio</h2>

		<input
			type="file"
			accept="audio/*"
			on:change={(e) => {
				masterAudio = e.currentTarget.files?.[0] || null;
			}}
		/>

		<button on:click={generateReference}>
			Generate Reference
		</button>
	</div>

	{#if reference}
		<div class="card">
			<h2>Reference Blueprint</h2>

			<h3>Words Timeline</h3>

			<div class="words">
				{#each reference.words as word}
					<div class="word">
						<b>{word.word}</b>
						<span>{word.start.toFixed(2)}s</span>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<div class="card">
		<h2>2. Upload Attempt</h2>

		<input
			type="file"
			accept="audio/*"
			on:change={(e) => {
				userAudio = e.currentTarget.files?.[0] || null;
			}}
		/>

		<button on:click={compareAttempt}>
			Compare Attempt
		</button>
	</div>

	{#if compare}
		<div class="card">
			<h2>Score</h2>

			<div class="score">
				{compare.score}%
			</div>
		</div>
	{/if}

	{#if loading}
		<div class="loading">
			Loading...
		</div>
	{/if}
</div>

<style>
	:global(body) {
		margin: 0;
		font-family: sans-serif;
		background: #111;
		color: white;
	}

	.container {
		max-width: 900px;
		margin: auto;
		padding: 40px;
	}

	.card {
		background: #1a1a1a;
		padding: 20px;
		margin-bottom: 20px;
		border-radius: 12px;
	}

	button {
		margin-top: 12px;
		padding: 10px 16px;
		cursor: pointer;
	}

	.words {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}

	.word {
		background: #222;
		padding: 10px;
		border-radius: 8px;
		display: flex;
		flex-direction: column;
	}

	.score {
		font-size: 48px;
		font-weight: bold;
	}
</style>
