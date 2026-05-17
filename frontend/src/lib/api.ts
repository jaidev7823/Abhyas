import axios from 'axios';

export const api = axios.create({
	baseURL: 'https://unrequited-tierra-nondiverging.ngrok-free.dev'
});

