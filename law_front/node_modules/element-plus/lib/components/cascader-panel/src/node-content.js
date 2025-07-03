'use strict';

Object.defineProperty(exports, '__esModule', { value: true });

var vue = require('vue');
var index = require('../../../hooks/use-namespace/index.js');

function isVNodeEmpty(vnodes) {
  return !!(vnodes == null ? void 0 : vnodes.every((vnode) => vnode.type === vue.Comment));
}
var NodeContent = vue.defineComponent({
  name: "NodeContent",
  setup() {
    const ns = index.useNamespace("cascader-node");
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
    return vue.h("span", { class: ns.e("label") }, label());
  }
});

exports["default"] = NodeContent;
//# sourceMappingURL=node-content.js.map
