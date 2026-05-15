export interface Word {
	word: string;
	start: number;
	end: number;
}

export interface PauseRegion {
	start: number;
	end: number;
}

export interface ReferenceData {
	words: Word[];
	times: number[];
	rms: number[];
	pitch: number[];
	pause_mask: boolean[];
	pause_regions: PauseRegion[];
	cps: number[];
	duration: number;
	sample_rate: number;
}

export interface ScoreData {
	overall: number;
	timing: number;
	pitch: number;
	rhythm: number;
	pacing: number;
}
