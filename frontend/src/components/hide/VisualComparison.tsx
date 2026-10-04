import { useState } from "react";
import { Eye } from "lucide-react";
import { Callout } from "@/components/ui/Callout";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Tabs } from "@/components/ui/Tabs";
import { CompareSlider } from "@/components/images/CompareSlider";
import { DifferenceMap, supportsDifferenceMap } from "@/components/images/DifferenceMap";

export function VisualComparison({
  coverId,
  stegoId,
  width,
  height,
  coverFormat,
}: {
  coverId: string;
  stegoId: string;
  width: number;
  height: number;
  /** Extension or MIME type of the original, to decide if a diff is reliable. */
  coverFormat?: string | null;
}) {
  const [view, setView] = useState<"slider" | "diff">("slider");
  const diffSupported = supportsDifferenceMap(coverFormat);

  return (
    <Card>
      <CardHeader
        icon={<Eye className="h-4 w-4" />}
        title="Can you spot the difference?"
        description="Drag the divider to compare the original with the image that now carries your message."
      />
      <Tabs
        label="Comparison view"
        value={view}
        onChange={setView}
        className="px-5"
        options={[
          { value: "slider", label: "Side by side" },
          { value: "diff", label: "Changed areas" },
        ]}
      />
      <CardBody>
        {view === "slider" ? (
          <CompareSlider beforeId={coverId} afterId={stegoId} width={width} height={height} />
        ) : diffSupported ? (
          <DifferenceMap beforeId={coverId} afterId={stegoId} />
        ) : (
          <Callout tone="info" title="Not available for JPEG or WebP originals">
            Browsers decode these formats slightly differently from the server,
            so a pixel-by-pixel map would wrongly show almost every pixel as
            changed. Use a PNG, BMP or TIFF original to see exactly which areas
            changed.
          </Callout>
        )}
      </CardBody>
    </Card>
  );
}
