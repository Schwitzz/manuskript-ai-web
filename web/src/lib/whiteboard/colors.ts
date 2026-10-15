export interface WhiteboardColorOption {
	id: string;
	label: string;
	value: string; // '' means theme accent / default
	swatch: string;
}

export const WHITEBOARD_COLORS: WhiteboardColorOption[] = [
	{ id: 'default', label: 'Theme Accent', value: '', swatch: 'var(--accent, #3b82f6)' },
	{ id: 'red', label: 'Red', value: '#ef4444', swatch: '#ef4444' },
	{ id: 'orange', label: 'Orange', value: '#f97316', swatch: '#f97316' },
	{ id: 'amber', label: 'Amber', value: '#eab308', swatch: '#eab308' },
	{ id: 'emerald', label: 'Emerald', value: '#22c55e', swatch: '#22c55e' },
	{ id: 'teal', label: 'Teal', value: '#14b8a6', swatch: '#14b8a6' },
	{ id: 'blue', label: 'Blue', value: '#3b82f6', swatch: '#3b82f6' },
	{ id: 'indigo', label: 'Indigo', value: '#6366f1', swatch: '#6366f1' },
	{ id: 'purple', label: 'Purple', value: '#a855f7', swatch: '#a855f7' },
	{ id: 'pink', label: 'Pink', value: '#ec4899', swatch: '#ec4899' },
	{ id: 'slate', label: 'Slate', value: '#64748b', swatch: '#64748b' }
];
