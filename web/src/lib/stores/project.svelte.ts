import { call } from '#lib/api.ts';

export interface ProjectItem {
	name: string;
	title: string;
}

let selectedProjectName = $state<string | null>(null);

async function fetchProjects(): Promise<ProjectItem[]> {
	try {
		const data = await call('GET /api/projects');
		return (data as any).projects;
	} catch {
		return [];
	}
}

function select(name: string) {
	selectedProjectName = name || null;
	if (name) {
		localStorage.setItem('msk_project', name);
	} else {
		localStorage.removeItem('msk_project');
	}
}

function init() {
	const saved = localStorage.getItem('msk_project');
	if (saved) selectedProjectName = saved;
}

init();

export const project = {
	get name() { return selectedProjectName; },
	select,
	fetchProjects
};
