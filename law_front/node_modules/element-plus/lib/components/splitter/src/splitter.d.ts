import type { ExtractPropTypes } from 'vue';
import type Splitter from './splitter.vue';
export declare const splitterProps: {
    readonly layout: import("element-plus/es/utils").EpPropFinalized<StringConstructor, "horizontal" | "vertical", unknown, "horizontal", boolean>;
};
export type SplitterProps = ExtractPropTypes<typeof splitterProps>;
export type SplitterInstance = InstanceType<typeof Splitter> & unknown;
