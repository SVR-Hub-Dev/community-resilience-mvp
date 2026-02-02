import { fail } from '@sveltejs/kit';
import type { Actions } from './$types';
import { backend } from '$lib/server/backend';

export const actions = {
	default: async ({ request }) => {
		const data = await request.formData();
		const email = data.get('email');

		if (!email || typeof email !== 'string') {
			return fail(400, { error: 'Email is required', email: '' });
		}

		try {
			await backend.requestPasswordReset(email);
			// Always return success to prevent email enumeration
			return { success: true };
		} catch (err) {
			console.error('Password reset request error:', err);
			// Still return success to prevent email enumeration
			// The user doesn't need to know if the email exists or not
			return { success: true };
		}
	}
} satisfies Actions;
