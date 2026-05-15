export interface Word {
	word: string;
	start: number;
	end: number;
}

export interface PauseRegion {
	start: number;
	end: number;
}

export interface SentenceSegment {
	id: number;
	index: number;
	text: string;
	start: number;
	end: number;
}

export interface ReferenceData {
	words: Word[];
	sentences?: SentenceSegment[];
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

export interface ComparisonResponse extends ScoreData {
	attempt?: ReferenceData;
}
