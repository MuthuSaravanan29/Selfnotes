import { defineStore } from "pinia";
import { ref } from "vue";

export const useGlobalStore = defineStore("global", () => {
  const config = ref({});
  const sidebarVisible = ref(true);
  const notesList = ref([]);
  const currentNoteTitle = ref("");

  function toggleSidebar() {
    sidebarVisible.value = !sidebarVisible.value;
  }

  return { config, sidebarVisible, notesList, currentNoteTitle, toggleSidebar };
});
