<script lang="ts">
	import type { ScoreData } from '$lib/types';

	let { score }: { score: ScoreData } = $props();

	function scoreColor(val: number): string {
		if (val >= 80) return '#4caf50';
		if (val >= 60) return '#ff9800';
		return '#f44336';
	}

	function arcPath(val: number): string {
		const r = 36;
		const circ = 2 * Math.PI * r;
		const offset = circ * (1 - val / 100);
		return `M ${r} 2 A ${r - 2} ${r - 2} 0 ${val > 50 ? 1 : 0} 1 ${r - 2} ${2 * r - 2}`;
	}
</script>

<div class="score-card">
	<div class="overall">
		<svg width="80" height="80" viewBox="0 0 80 80">
			<circle cx="40" cy="40" r="36" fill="none" stroke="#333" stroke-width="4" />
			<circle
				cx="40" cy="40" r="36"
				fill="none" stroke={scoreColor(score.overall)}
				stroke-width="4"
				stroke-dasharray="226.2"
				stroke-dashoffset={226.2 * (1 - score.overall / 100)}
				stroke-linecap="round"
				transform="rotate(-90 40 40)"
			/>
			<text x="40" y="40" text-anchor="middle" dominant-baseline="central" fill="white" font-size="20" font-weight="bold">
				{score.overall}
			</text>
		</svg>
		<div class="overall-label">Overall</div>
	</div>

	<div class="sub-scores">
		{#each Object.entries({ Timing: score.timing, Pitch: score.pitch, Rhythm: score.rhythm, Pacing: score.pacing }) as [label, val]}
			<div class="sub-score">
				<div class="sub-label">{label}</div>
				<div class="sub-bar">
      <div class="sub-fill" style="width: {val}%; background: {scoreColor(val)};"></div>
      
				</div>
				<div class="sub-val" style="color: {scoreColor(val)};">{val}</div>
			</div>
		{/each}
	</div>
</div>

<style>
	.score-card {
		background: #1a1a1a;
		border-radius: 12px;
		padding: 24px;
		display: flex;
		gap: 32px;
		align-items: center;
	}
	.overall {
		text-align: center;
		flex-shrink: 0;
	}
	.overall-label {
		color: #888;
		font-size: 12px;
		margin-top: 4px;
		text-transform: uppercase;
		letter-spacing: 1px;
	}
	.sub-scores {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.sub-score {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.sub-label {
		width: 60px;
		color: #ccc;
		font-size: 13px;
		font-weight: 500;
		text-align: right;
	}
	.sub-bar {
		flex: 1;
		height: 8px;
		background: #333;
		border-radius: 4px;
		overflow: hidden;
	}
	.sub-fill {
		height: 100%;
		border-radius: 4px;
		transition: width 0.5s ease;
	}
	.sub-val {
		width: 36px;
		font-size: 14px;
		font-weight: 700;
		text-align: right;
	}
</style>
