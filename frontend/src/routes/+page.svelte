<cript lang="ts">

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

	.pre {
		overflow: auto;
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
