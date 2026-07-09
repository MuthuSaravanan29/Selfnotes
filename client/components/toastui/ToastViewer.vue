<template>
  <div ref="viewerElement"></div>
</template>

<script setup>
import Viewer from "@toast-ui/editor/dist/toastui-editor-viewer";
import { onMounted, ref } from "vue";

import baseOptions from "./baseOptions.js";
import extendedAutolinks from "./extendedAutolinks.js";

const props = defineProps({
  initialValue: String,
});

const viewerElement = ref();
let viewer;

onMounted(() => {
  viewer = new Viewer({
    ...baseOptions,
    extendedAutolinks,
    el: viewerElement.value,
    initialValue: props.initialValue,
  });
});

function setMarkdown(markdown) {
  if (viewer) {
    viewer.setMarkdown(markdown);
  }
}

defineExpose({ setMarkdown });
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor-viewer.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "./toastui-editor-overrides.scss";
</style>
