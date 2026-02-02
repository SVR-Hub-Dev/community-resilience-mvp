import { fail, redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import { backend } from '$lib/server/backend';

export const actions = {
	default: async ({ request }) => {
		const data = await request.formData();
		const token = data.get('token');
		const password = data.get('password');
		const confirmPassword = data.get('confirmPassword');

		if (!token || typeof token !== 'string') {
			return fail(400, { error: 'Reset token is required' });
		}

		if (!password || typeof password !== 'string') {
			return fail(400, { error: 'Password is required' });
		}

		if (!confirmPassword || typeof confirmPassword !== 'string') {
			return fail(400, { error: 'Please confirm your password' });
		}

		if (password !== confirmPassword) {
			return fail(400, { error: 'Passwords do not match' });
		}

		if (password.length < 8) {
			return fail(400, { error: 'Password must be at least 8 characters long' });
		}

		try {
			await backend.resetPassword(token, password);
			return { success: true };
		} catch (err) {
			console.error('Password reset error:', err);
			return fail(400, {
				error: 'Invalid or expired reset token. Please request a new password reset link.'
			});
		}
	}
} satisfies Actions;
