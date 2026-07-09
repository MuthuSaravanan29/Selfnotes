import { createNote, getNote } from "./api.js";
import router from "./router.js";

export async function openDailyNote() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  const title = `${year}-${month}-${day}`;

  try {
    await getNote(title);
  } catch (error) {
    if (error.response?.status === 404) {
      const template = `# ${title}\n\n## Today\n\n## Tasks\n\n## Notes\n`;
      await createNote(title, template);
    } else {
      throw error;
    }
  }

  router.push({ name: "note", params: { title } });
}
