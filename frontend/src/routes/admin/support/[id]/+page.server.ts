import { fail, redirect, error } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { createApiClient, ApiError } from '$lib/server/api';
import type { TicketDetail, TicketResponse, SupportTicket, User } from '$lib/types';

export const load: PageServerLoad = async ({ locals, params }) => {
	if (!locals.user) {
		throw redirect(302, '/auth/login?redirect=/admin/support/' + params.id);
	}

	if (locals.user.role !== 'admin') {
		throw error(403, 'Admin access required');
	}

	const api = createApiClient(locals.user);
	const ticketId = parseInt(params.id, 10);

	if (isNaN(ticketId)) {
		throw error(400, 'Invalid ticket ID');
	}

	try {
		const ticket = await api.get<TicketDetail>(`/admin/support/tickets/${ticketId}`);

		// Also fetch list of admin users for assignment
		let admins: User[] = [];
		try {
			const usersData = await api.get<{ users: User[]; total: number }>('/auth/users?role=admin');
			admins = usersData.users;
		} catch {
			// Non-critical, continue without admins list
		}

		return { ticket, admins };
	} catch (err) {
		if (err instanceof ApiError) {
			if (err.status === 404) {
				throw error(404, 'Ticket not found');
			}
		}
		console.error('Failed to load ticket:', err);
		throw error(500, 'Failed to load ticket');
	}
};

export const actions = {
	update: async ({ request, locals, params }) => {
		if (!locals.user || locals.user.role !== 'admin') {
			throw redirect(302, '/auth/login');
		}

		const data = await request.formData();
		const status = data.get('status') as string;
		const priority = data.get('priority') as string;
		const assignedTo = data.get('assigned_to') as string;
		const ticketId = parseInt(params.id, 10);

		const api = createApiClient(locals.user);

		try {
			const updateData: Record<string, unknown> = {};
			if (status) updateData.status = status;
			if (priority) updateData.priority = priority;
			if (assignedTo) updateData.assigned_to = parseInt(assignedTo, 10);

			await api.put<SupportTicket>(`/admin/support/tickets/${ticketId}`, updateData);

			return { updateSuccess: true };
		} catch (err) {
			console.error('Failed to update ticket:', err);
			return fail(500, { updateError: 'Failed to update ticket' });
		}
	},

	respond: async ({ request, locals, params }) => {
		if (!locals.user || locals.user.role !== 'admin') {
			throw redirect(302, '/auth/login');
		}

		const data = await request.formData();
		const message = data.get('message');
		const isInternal = data.get('is_internal') === 'on';
		const ticketId = parseInt(params.id, 10);

		if (!message || typeof message !== 'string' || message.trim().length === 0) {
			return fail(400, { responseError: 'Message is required' });
		}

		const api = createApiClient(locals.user);

		try {
			await api.post<TicketResponse>(`/admin/support/tickets/${ticketId}/responses`, {
				message: message.trim(),
				is_internal: isInternal,
			});

			return { responseSuccess: true };
		} catch (err) {
			console.error('Failed to add response:', err);
			return fail(500, { responseError: 'Failed to add response' });
		}
	},
} satisfies Actions;
