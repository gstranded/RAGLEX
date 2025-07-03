import { defineComponent, h, Comment } from 'vue';
import { useNamespace } from '../../../hooks/use-namespace/index.mjs';

function isVNodeEmpty(vnodes) {
  return !!(vnodes == null ? void 0 : vnodes.every((vnode) => vnode.type === Comment));
}
var NodeContent = defineComponent({
  name: "NodeContent",
  setup() {
    const ns = useNamespace("cascader-node");
    return {
      ns
    };
  },
  render() {
    const { ns } = this;
    const { node, panel } = this.$parent;
    const { data, label: nodeLabel } = node;
    const { renderLabelFn } = panel;
    const label = () => {
      let renderLabel = renderLabelFn == null ? void 0 : renderLabelFn({ node, data });
      if (isVNodeEmpty(renderLabel)) {
        renderLabel = nodeLabel;
      }
      return renderLabel != null ? renderLabel : nodeLabel;
    };
    return h("span", { class: ns.e("label") }, label());
  }
});

export { NodeContent as default };
//# sourceMappingURL=node-content.mjs.map
