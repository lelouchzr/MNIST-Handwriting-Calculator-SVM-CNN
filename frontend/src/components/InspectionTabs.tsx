import type { ReactNode } from "react";
import { Tabs } from "@base-ui/react/tabs";

export const inspectionTabs = ["Input", "Predictions", "Explanation"] as const;
export type InspectionTab = (typeof inspectionTabs)[number];

export function InspectionTabs({
  value,
  onChange,
  comparison = false,
  children,
}: {
  value: InspectionTab;
  onChange: (value: InspectionTab) => void;
  comparison?: boolean;
  children: ReactNode;
}) {
  return (
    <Tabs.Root
      className="inspection-tabs-root"
      value={value}
      onValueChange={(next) => onChange(next as InspectionTab)}
    >
      <Tabs.List
        className="inspector-tabs"
        activateOnFocus
        aria-label={
          comparison ? "Model comparison inspection" : "Recognition inspection"
        }
      >
        {inspectionTabs.map((name) => (
          <Tabs.Tab key={name} value={name}>
            {name}
          </Tabs.Tab>
        ))}
      </Tabs.List>
      {inspectionTabs.map((name) => (
        <Tabs.Panel
          key={name}
          value={name}
          className={
            comparison ? "comparison-tab-content" : "inspector-content"
          }
        >
          {value === name ? children : null}
        </Tabs.Panel>
      ))}
    </Tabs.Root>
  );
}
