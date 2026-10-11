/** Simple toast store for undo-style notifications. */

interface Toast {
	id: string;
	message: string;
	actionLabel?: string;
	onAction?: () => void;
}

let toasts = $state<Toast[]>([]);

export function addToast(message: string, opts?: { actionLabel?: string; onAction?: () => void }) {
	const id = crypto.randomUUID?.() ?? String(Date.now());
	toasts.push({ id, message, ...opts });
	setTimeout(() => {
		toasts = toasts.filter(t => t.id !== id);
	}, 5000);
	return id;
}

export function undoAfter(label: string, onDelete: () => void, onRestore: () => void) {
	return addToast(`${label} deleted`, {
		actionLabel: 'Undo',
		onAction: () => { onRestore(); onDelete(); }
	});
}

export function removeToast(id: string) {
	toasts = toasts.filter(t => t.id !== id);
}

export function toastStore() {
	function getToasts() { return toasts; }
	function setToasts(t: Toast[]) { toasts = t; }
	return {
		get: getToasts,
		set: setToasts
	};
}
