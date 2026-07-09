<template>
  <ConfirmModal
    v-model="isDeleteModalVisible"
    title="Confirm Deletion"
    :message="`Are you sure you want to delete the note '${note.title}'?`"
    confirmButtonText="Delete"
    confirmButtonStyle="danger"
    @confirm="deleteConfirmedHandler"
  />

  <ConfirmModal
    v-model="isSaveChangesModalVisible"
    title="Save Changes"
    message="Do you want to save your changes?"
    confirmButtonText="Save"
    confirmButtonStyle="success"
    rejectButtonText="Discard"
    rejectButtonStyle="danger"
    @confirm="saveHandler((close = true))"
    @reject="closeNote"
  />

  <ConfirmModal
    v-model="isDraftModalVisible"
    title="Draft Detected"
    message="There is an unsaved draft of this note stored in this browser. Do you want to resume the draft version or delete it?"
    confirmButtonText="Resume Draft"
    confirmButtonStyle="cta"
    rejectButtonText="Delete Draft"
    rejectButtonStyle="danger"
    @confirm="setEditMode()"
    @reject="clearDraft(); setEditMode()"
  />

  <LoadingIndicator ref="loadingIndicator" class="flex h-full flex-col">
    <!-- Header -->
    <div class="mb-3 flex flex-col-reverse md:flex-row md:items-baseline">
      <div class="grow truncate text-2xl leading-[1.6em]">
        <span v-show="!editMode && !splitEditMode" :title="note.title">{{ note.title }}</span>
        <input
          v-show="editMode || splitEditMode"
          v-model.trim="newTitle"
          class="w-full bg-transparent text-2xl outline-none"
          placeholder="Title"
        />
      </div>

      <div class="flex shrink-0 self-end md:self-baseline print:hidden">
        <CustomButton
          v-show="canModify && !isNewNote"
          label="Delete"
          :iconPath="mdilDelete"
          @click="deleteHandler"
        />
        <CustomButton
          v-show="editMode || splitEditMode"
          label="Save"
          :iconPath="mdilContentSave"
          class="relative ml-1"
          @click="saveHandler((close = false))"
        >
          <div
            v-show="unsavedChanges"
            class="absolute right-1 h-1.5 w-1.5 rounded-full bg-theme-brand"
          ></div>
        </CustomButton>
        <button
          v-if="canModify"
          class="ml-1 rounded px-2 py-1 text-sm text-theme-text-muted hover:bg-theme-background-elevated"
          :class="{ 'bg-theme-background-elevated text-theme-text': splitEditMode }"
          title="Split pane (editor + preview)"
          @click="toggleSplitMode"
        >
          <SvgIcon type="mdi" :path="mdiViewSplitHorizontal" size="1.25em" />
        </button>
        <Toggle
          v-if="canModify"
          label="Edit"
          :isOn="editMode || splitEditMode"
          class="ml-1"
          @click="toggleEditModeHandler"
        />
      </div>
    </div>

    <hr v-if="!editMode && !splitEditMode" class="mb-4 border-theme-border" />

    <!-- Content: Split Mode -->
    <div v-if="splitEditMode" class="flex flex-1 gap-4 overflow-hidden">
      <div class="flex-1 overflow-y-auto">
        <ToastEditor
          ref="toastEditor"
          :initialValue="getInitialEditorValue()"
          :initialEditType="'markdown'"
          :addImageBlobHook="addImageBlobHook"
          @change="startContentChangedTimeout"
          @keydown="keydownHandler"
        />
      </div>
      <div class="flex-1 overflow-y-auto border-l border-theme-border pl-4">
        <ToastViewer
          ref="toastViewer"
          :key="'split-' + viewerKey"
          :initialValue="toastEditor?.getMarkdown() || note.content"
          class="toast-viewer"
        />
      </div>
    </div>

    <!-- Content: Edit Mode -->
    <div v-else-if="editMode" class="flex-1">
      <ToastEditor
        ref="toastEditor"
        :initialValue="getInitialEditorValue()"
        :initialEditType="loadDefaultEditorMode()"
        :addImageBlobHook="addImageBlobHook"
        @change="startContentChangedTimeout"
        @keydown="keydownHandler"
      />
    </div>

    <!-- Content: View Mode -->
    <div v-else class="flex-1">
      <ToastViewer
        ref="toastViewer"
        :initialValue="note.content"
        class="toast-viewer pb-4"
      />
      <BacklinksPanel :title="note.title" />
    </div>
  </LoadingIndicator>
</template>

<style>
.toast-viewer li.task-list-item {
  pointer-events: none;
}
.toast-viewer li.task-list-item a {
  pointer-events: auto;
}
</style>

<script setup>
import { mdiNoteOffOutline } from "@mdi/js";
import { mdilContentSave, mdilDelete } from "@mdi/light-js";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiViewSplitHorizontal } from "@mdi/js";
import Mousetrap from "mousetrap";
import { useToast } from "primevue/usetoast";
import { computed, nextTick, onMounted, ref, watch, watchEffect } from "vue";
import { useRouter } from "vue-router";

import {
  apiErrorHandler,
  createAttachment,
  createNote,
  deleteNote,
  getNote,
  updateNote,
} from "../api.js";
import { Note } from "../classes.js";
import ConfirmModal from "../components/ConfirmModal.vue";
import CustomButton from "../components/CustomButton.vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import Toggle from "../components/Toggle.vue";
import ToastEditor from "../components/toastui/ToastEditor.vue";
import ToastViewer from "../components/toastui/ToastViewer.vue";
import BacklinksPanel from "../components/BacklinksPanel.vue";
import { authTypes } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { getToastOptions } from "../helpers.js";
import { isCurrentTokenStored } from "../tokenStorage.js";

const props = defineProps({
  title: String,
});

const canModify = computed(() => globalStore.config.authType != authTypes.readOnly);
let contentChangedTimeout;
const editMode = ref(false);
const splitEditMode = ref(false);
const globalStore = useGlobalStore();
const isSaveChangesModalVisible = ref(false);
const isDeleteModalVisible = ref(false);
const isDraftModalVisible = ref(false);
const isNewNote = computed(() => !props.title);
const loadingIndicator = ref();
const note = ref({});
const reservedFilenameCharacters = /[<>:"/\\|?*]/;
const router = useRouter();
const newTitle = ref();
const toast = useToast();
const toastEditor = ref();
const toastViewer = ref();
const unsavedChanges = ref(false);
const viewerKey = ref(0);

function init() {
  if (props.title && props.title == note.value.title) {
    return;
  }

  loadingIndicator.value.setLoading();
  if (props.title) {
    setActiveNote(props.title);
    getNote(props.title)
      .then((data) => {
        note.value = data;
        setActiveNote(data.title);
        loadingIndicator.value.setLoaded();
      })
      .catch((error) => {
        if (error.response?.status === 404) {
          loadingIndicator.value.setFailed("Note not found", mdiNoteOffOutline);
        } else {
          loadingIndicator.value.setFailed();
          apiErrorHandler(error, toast);
        }
      });
  } else {
    newTitle.value = "";
    note.value = new Note();
    editMode.value = false;
    splitEditMode.value = false;
    nextTick(() => {
      editHandler();
      loadingIndicator.value.setLoaded();
    });
  }
}

function setActiveNote(title) {
  globalStore.currentNoteTitle = title;
}

function toggleSplitMode() {
  if (splitEditMode.value) {
    splitEditMode.value = false;
  } else {
    if (editMode.value) {
      editMode.value = false;
    }
    splitEditMode.value = true;
    if (!newTitle.value) {
      newTitle.value = note.value.title;
    }
  }
}

function toggleEditModeHandler() {
  if (editMode.value || splitEditMode.value) {
    closeHandler();
  } else {
    editHandler();
  }
}

function editHandler() {
  splitEditMode.value = false;
  const draftContent = loadDraft();
  if (draftContent) {
    isDraftModalVisible.value = true;
  } else {
    setEditMode();
  }
}

function setEditMode() {
  newTitle.value = note.value.title;
  unsavedChanges.value = false;
  editMode.value = true;
  splitEditMode.value = false;
}

function getInitialEditorValue() {
  const draftContent = loadDraft();
  return draftContent || note.value.content;
}

function deleteHandler() {
  isDeleteModalVisible.value = true;
}

function deleteConfirmedHandler() {
  deleteNote(note.value.title)
    .then(() => {
      toast.add(getToastOptions("Note deleted ✓", "Success", "success"));
      setActiveNote("");
      router.push({ name: "home" });
    })
    .catch((error) => {
      apiErrorHandler(error, toast);
    });
}

function saveHandler(close = false) {
  saveDefaultEditorMode();
  if (!newTitle.value) {
    toast.add(getToastOptions("Cannot save note without a title.", "Invalid", "error"));
    return;
  }
  if (reservedFilenameCharacters.test(newTitle.value)) {
    badFilenameToast("Title");
    return;
  }

  let newContent = toastEditor.value.getMarkdown();
  if (isNewNote.value) {
    saveNew(newTitle.value, newContent, close);
  } else {
    saveExisting(newTitle.value, newContent, close);
  }
}

function saveNew(newTitle, newContent, close = false) {
  createNote(newTitle, newContent)
    .then((data) => {
      clearDraft();
      note.value = data;
      setActiveNote(data.title);
      router.push({ name: "note", params: { title: note.value.title } })
        .then(() => { noteSaveSuccess(close); });
    })
    .catch(noteSaveFailure);
}

function saveExisting(newTitle, newContent, close = false) {
  if (newTitle == note.value.title && newContent == note.value.content) {
    noteSaveSuccess(close);
    return;
  }
  updateNote(note.value.title, newTitle, newContent)
    .then((data) => {
      clearDraft();
      note.value = data;
      setActiveNote(data.title);
      router.replace({ name: "note", params: { title: note.value.title } });
      noteSaveSuccess(close);
    })
    .catch(noteSaveFailure);
}

function noteSaveFailure(error) {
  if (error.response?.status === 409) {
    toast.add(getToastOptions("A note with this title already exists. Please try again with a new title.", "Duplicate", "error"));
  } else if (error.response?.status === 413) {
    entityTooLargeToast("note");
  } else {
    apiErrorHandler(error, toast);
  }
}

function noteSaveSuccess(close = false) {
  unsavedChanges.value = false;
  if (close) {
    closeNote();
  }
  setBeforeUnloadConfirmation(false);
  toast.add(getToastOptions("Note saved successfully ✓", "Success", "success"));
}

function closeHandler() {
  if (isContentChanged()) {
    isSaveChangesModalVisible.value = true;
  } else {
    closeNote();
  }
}

function closeNote() {
  clearDraft();
  editMode.value = false;
  splitEditMode.value = false;
  if (isNewNote.value) {
    router.push({ name: "home" });
  }
}

function addImageBlobHook(file, callback) {
  const altTextInputValue = document.getElementById("toastuiAltTextInput")?.value;
  postAttachment(file).then(function (data) {
    if (data) {
      callback(data.url, altTextInputValue || data.filename);
    }
  });
}

function postAttachment(file) {
  if (reservedFilenameCharacters.test(file.name)) {
    badFilenameToast("Filename");
    return;
  }
  toast.add(getToastOptions("Uploading attachment..."));
  return createAttachment(file)
    .then((data) => {
      toast.add(getToastOptions("Attachment uploaded successfully ✓", "Success", "success"));
      return data;
    })
    .catch((error) => {
      if (error.response?.status === 409) {
        toast.add(getToastOptions("An attachment with this filename already exists.", "Duplicate", "error"));
      } else if (error.response?.status == 413) {
        entityTooLargeToast("attachment");
      } else {
        apiErrorHandler(error, toast);
      }
    });
}

function startContentChangedTimeout() {
  clearContentChangedTimeout();
  contentChangedTimeout = setTimeout(contentChangedHandler, 1000);
}

function clearContentChangedTimeout() {
  if (contentChangedTimeout != null) {
    clearTimeout(contentChangedTimeout);
  }
}

function contentChangedHandler() {
  if (isContentChanged()) {
    unsavedChanges.value = true;
    setBeforeUnloadConfirmation(true);
    saveDraft();
  } else {
    unsavedChanges.value = false;
    setBeforeUnloadConfirmation(false);
    clearDraft();
  }
}

function saveDraft() {
  const content = toastEditor.value.getMarkdown();
  const userHasPersistedToken = isCurrentTokenStored();
  if (content) {
    if (userHasPersistedToken) {
      localStorage.setItem(note.value.title, content);
    } else {
      sessionStorage.setItem(note.value.title, content);
    }
  }
}

function clearDraft() {
  localStorage.removeItem(note.value.title);
  sessionStorage.removeItem(note.value.title);
}

function loadDraft() {
  const localDraft = localStorage.getItem(note.value.title);
  const sessionDraft = sessionStorage.getItem(note.value.title);
  return localDraft || sessionDraft;
}

Mousetrap.bind("e", () => {
  if (editMode.value === false && splitEditMode.value === false && canModify.value) {
    editHandler();
  }
});

function keydownHandler(event) {
  if ((event.ctrlKey || event.metaKey) && event.key == "Enter") {
    saveHandler((close = false));
  }
  if (event.key == "Escape") {
    closeHandler();
  }
}

function entityTooLargeToast(entityName) {
  toast.add(getToastOptions(`This ${entityName} is too large. Please try again with a smaller ${entityName} or adjust your server configuration.`, "Failure", "error"));
}

function badFilenameToast(entityName) {
  toast.add(getToastOptions('Due to filename restrictions, the following characters are not allowed: <>:"/\\|?*', `Invalid ${entityName}`, "error"));
}

function setBeforeUnloadConfirmation(enable = true) {
  if (enable) {
    window.onbeforeunload = () => true;
  } else {
    window.onbeforeunload = null;
  }
}

function saveDefaultEditorMode() {
  const isWysiwygMode = toastEditor.value.isWysiwygMode();
  localStorage.setItem("defaultEditorMode", isWysiwygMode ? "wysiwyg" : "markdown");
}

function loadDefaultEditorMode() {
  const defaultWysiwygMode = localStorage.getItem("defaultEditorMode");
  return defaultWysiwygMode || "markdown";
}

function isContentChanged() {
  return newTitle.value != note.value.title || toastEditor.value.getMarkdown() != note.value.content;
}

watch(
  () => props.title,
  (newTitle) => {
    if (newTitle) setActiveNote(newTitle);
    init();
  },
);
onMounted(init);

// Live preview sync for split mode
watchEffect(() => {
  if (splitEditMode.value && toastViewer.value && toastEditor.value) {
    const timer = setInterval(() => {
      if (toastEditor.value && toastViewer.value) {
        toastViewer.value.setMarkdown(toastEditor.value.getMarkdown());
      }
    }, 500);
    return () => clearInterval(timer);
  }
});
</script>
