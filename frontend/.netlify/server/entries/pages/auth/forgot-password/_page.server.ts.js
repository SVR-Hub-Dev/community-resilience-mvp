import { fail } from "@sveltejs/kit";
import { b as backend } from "../../../../chunks/backend.js";
const actions = {
  default: async ({ request }) => {
    const data = await request.formData();
    const email = data.get("email");
    if (!email || typeof email !== "string") {
      return fail(400, { error: "Email is required", email: "" });
    }
    try {
      await backend.requestPasswordReset(email);
      return { success: true };
    } catch (err) {
      console.error("Password reset request error:", err);
      return { success: true };
    }
  }
};
export {
  actions
};
