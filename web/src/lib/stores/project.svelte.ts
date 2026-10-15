import { call } from '#lib/api.ts';

export interface ProjectItem {
	name: string;
	title: string;
}

let selectedProjectName = $state<string | null>(null);

async function fetchProjects(): Promise<ProjectItem[]> {
	try {
		const data = await call('GET /api/projects');
		const list = ((data as any).projects ?? []) as ProjectItem[];
		if (list.length > 0) {
			const exists = list.some((p) => p.name === selectedProjectName);
			if (!selectedProjectName || !exists) {
				select(list[0].name);
			}
		} else if (selectedProjectName) {
			select('');
		}
		return list;
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
