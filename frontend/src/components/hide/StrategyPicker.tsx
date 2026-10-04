import { Sparkles, SlidersHorizontal } from "lucide-react";
import { METHOD_INFO, type MethodCode } from "@/lib/describe";
import { cn } from "@/lib/cn";
import { Field, Select } from "@/components/ui/Field";
import { SegmentedControl } from "@/components/ui/Tabs";
import { HIDE_PRESETS, type PresetId } from "./presets";

export type Strategy = "auto" | "manual";

export interface ManualSettings {
  method: MethodCode;
  channelMode: string;
  lsbBits: number;
}

export function StrategyPicker({
  strategy,
  onStrategyChange,
  preset,
  onPresetChange,
  manual,
  onManualChange,
  saveReport,
  onSaveReportChange,
}: {
  strategy: Strategy;
  onStrategyChange: (strategy: Strategy) => void;
  preset: PresetId;
  onPresetChange: (preset: PresetId) => void;
  manual: ManualSettings;
  onManualChange: (settings: ManualSettings) => void;
  saveReport: boolean;
  onSaveReportChange: (value: boolean) => void;
}) {
  return (
    <div className="space-y-3">
      <SegmentedControl
        label="How the hiding method is chosen"
        value={strategy}
        onChange={onStrategyChange}
        className="w-full sm:w-auto"
        options={[
          { value: "auto", label: "Automatic", icon: <Sparkles className="h-3.5 w-3.5" aria-hidden /> },
          { value: "manual", label: "Choose myself", icon: <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden /> },
        ]}
      />

      {strategy === "auto" ? (
        <div className="space-y-3">
          <p className="text-xs leading-relaxed text-muted">
            StegoLab tries every method, verifies each result and keeps the best.
            What matters most to you?
          </p>

          <fieldset className="min-w-0">
            <legend className="sr-only">Priority</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {HIDE_PRESETS.map((option) => (
                <label
                  key={option.id}
                  className={cn(
                    "flex cursor-pointer gap-2.5 rounded-lg border px-3 py-2.5 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent",
                    preset === option.id
                      ? "border-accent bg-accent-soft/60"
                      : "border-line hover:border-line-strong hover:bg-elevated/50",
                  )}
                >
                  <input
                    type="radio"
                    name="hide-preset"
                    value={option.id}
                    checked={preset === option.id}
                    onChange={() => onPresetChange(option.id)}
                    className="mt-0.5 h-4 w-4 shrink-0 accent-[rgb(var(--accent))]"
                  />
                  <span className="min-w-0">
                    <span className="flex flex-wrap items-center gap-1.5 text-sm font-medium leading-5 text-fg">
                      {option.title}
                      {option.recommended && (
                        <span className="rounded-full bg-accent-soft px-1.5 text-[11px] font-medium text-accent">
                          Recommended
                        </span>
                      )}
                    </span>
                    <span className="block text-xs leading-snug text-muted">{option.description}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <label className="flex cursor-pointer items-start gap-2.5 rounded-lg bg-elevated/50 px-3 py-2.5 text-sm">
            <input
              type="checkbox"
              checked={saveReport}
              onChange={(event) => onSaveReportChange(event.target.checked)}
              className="mt-0.5 h-4 w-4 shrink-0 accent-[rgb(var(--accent))]"
            />
            <span>
              <span className="font-medium text-fg">Save a detection report for the result</span>
              <span className="block text-xs leading-snug text-muted">
                Runs the detector on the final image and adds it to your history.
              </span>
            </span>
          </label>
        </div>
      ) : (
        <div className="space-y-3">
          <Field
            label="Hiding method"
            help={METHOD_INFO[manual.method].summary}
          >
            <Select
              value={manual.method}
              onChange={(event) =>
                onManualChange({ ...manual, method: event.target.value as MethodCode })
              }
            >
              {(Object.keys(METHOD_INFO) as MethodCode[]).map((code) => (
                <option key={code} value={code}>
                  {METHOD_INFO[code].name}
                </option>
              ))}
            </Select>
          </Field>

          {manual.method === "LSB" && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Colour channels" help="Which colours carry the message.">
                <Select
                  value={manual.channelMode}
                  onChange={(event) => onManualChange({ ...manual, channelMode: event.target.value })}
                >
                  <option value="RGB">All colours (most room)</option>
                  <option value="R">Red only</option>
                  <option value="G">Green only</option>
                  <option value="B">Blue only</option>
                </Select>
              </Field>
              <Field label="Bits per colour value" help="More bits = more room, more change.">
                <Select
                  value={manual.lsbBits}
                  onChange={(event) => onManualChange({ ...manual, lsbBits: Number(event.target.value) })}
                >
                  <option value={1}>1 bit (least change)</option>
                  <option value={2}>2 bits</option>
                  <option value={3}>3 bits (most room)</option>
                </Select>
              </Field>
            </div>
          )}

          <p className="text-xs leading-relaxed text-muted">
            Manual mode runs only the method you pick, without comparing
            alternatives or saving a detection report. Useful for experiments
            and baselines.
          </p>
        </div>
      )}
    </div>
  );
}
