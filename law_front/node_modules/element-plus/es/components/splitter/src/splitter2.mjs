import { defineComponent, toRef, getCurrentInstance, watch, provide, reactive, openBlock, createElementBlock, normalizeClass, unref, renderSlot, createCommentVNode } from 'vue';
import { splitterProps } from './splitter.mjs';
import { splitterRootContextKey } from './type.mjs';
import _export_sfc from '../../../_virtual/plugin-vue_export-helper.mjs';
import { useContainer } from './hooks/useContainer.mjs';
import { useSize } from './hooks/useSize.mjs';
import { useResize } from './hooks/useResize.mjs';
import { useNamespace } from '../../../hooks/use-namespace/index.mjs';
import { useOrderedChildren } from '../../../hooks/use-ordered-children/index.mjs';

const __default__ = defineComponent({
  name: "ElSplitter"
});
const _sfc_main = /* @__PURE__ */ defineComponent({
  ...__default__,
  props: splitterProps,
  emits: ["resizeStart", "resize", "resizeEnd"],
  setup(__props, { emit: emits }) {
    const props = __props;
    const ns = useNamespace("splitter");
    const { containerEl, containerSize } = useContainer(toRef(props, "layout"));
    const {
      removeChild: unregisterPanel,
      children: panels,
      addChild: sortPanel
    } = useOrderedChildren(getCurrentInstance(), "ElSplitterPanel");
    watch(panels, () => {
      panels.value.forEach((instance, index) => {
        instance.setIndex(index);
      });
    });
    const { percentSizes, pxSizes } = useSize(panels, containerSize);
    const { onMoveStart, onMoving, onMoveEnd, onCollapse, movingIndex } = useResize(panels, containerSize, pxSizes);
    const onResizeStart = (index) => {
      onMoveStart(index);
      emits("resizeStart", index, pxSizes.value);
    };
    const onResize = (index, offset) => {
      onMoving(index, offset);
      emits("resize", index, pxSizes.value);
    };
    const onResizeEnd = (index) => {
      onMoveEnd();
      emits("resizeEnd", index, pxSizes.value);
    };
    provide(splitterRootContextKey, reactive({
      panels,
      percentSizes,
      pxSizes,
      layout: props.layout,
      movingIndex,
      containerSize,
      onMoveStart: onResizeStart,
      onMoving: onResize,
      onMoveEnd: onResizeEnd,
      onCollapse,
      registerPanel: (panel) => {
        panels.value.push(panel);
      },
      sortPanel,
      unregisterPanel
    }));
    return (_ctx, _cache) => {
      return openBlock(), createElementBlock("div", {
        ref_key: "containerEl",
        ref: containerEl,
        class: normalizeClass([unref(ns).b(), unref(ns).e(_ctx.layout)])
      }, [
        renderSlot(_ctx.$slots, "default"),
        createCommentVNode(" Prevent iframe touch events from breaking "),
        unref(movingIndex) ? (openBlock(), createElementBlock("div", {
          key: 0,
          class: normalizeClass([unref(ns).e("mask"), unref(ns).e(`mask-${_ctx.layout}`)])
        }, null, 2)) : createCommentVNode("v-if", true)
      ], 2);
    };
  }
});
var Splitter = /* @__PURE__ */ _export_sfc(_sfc_main, [["__file", "splitter.vue"]]);

export { Splitter as default };
//# sourceMappingURL=splitter2.mjs.map
