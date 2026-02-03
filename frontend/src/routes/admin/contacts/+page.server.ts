import { fail, redirect, error } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { createApiClient } from '$lib/server/api';
import type { ContactListResponse } from '$lib/types';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.user) {
		throw redirect(302, '/auth/login?redirect=/admin/contacts');
	}

	if (locals.user.role !== 'admin') {
		throw error(403, 'Admin access required');
	}

	const api = createApiClient(locals.user);

	try {
		const data = await api.get<ContactListResponse>('/admin/support/contacts');
		return {
			contacts: data.contacts,
			total: data.total,
		};
	} catch (err) {
		console.error('Failed to load contacts:', err);
		return {
			contacts: [],
			total: 0,
			error: 'Failed to load contacts',
		};
	}
};

export const actions = {
	markRead: async ({ request, locals }) => {
		if (!locals.user || locals.user.role !== 'admin') {
			throw redirect(302, '/auth/login');
		}

		const data = await request.formData();
		const contactId = data.get('contact_id');

		if (!contactId || typeof contactId !== 'string') {
			return fail(400, { error: 'Contact ID is required' });
		}

		const api = createApiClient(locals.user);

		try {
			await api.put(`/admin/support/contacts/${contactId}/read`);
			return { success: true };
		} catch (err) {
			console.error('Failed to mark contact as read:', err);
			return fail(500, { error: 'Failed to mark as read' });
		}
	},
} satisfies Actions;
