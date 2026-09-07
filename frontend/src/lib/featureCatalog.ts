/**
 * Display metadata for the 18 features used by the production
 * Random Forest steganalysis model.
 *
 * The `key` values are the exact feature names the backend produces and
 * must never be renamed — only the label shown to the user differs.
 */

export interface FeatureDescriptor {
  key: string;
  label: string;
  description: string;
  /** Typical display precision. */
  digits?: number;
}

export interface FeatureGroup {
  id: string;
  title: string;
  blurb: string;
  features: FeatureDescriptor[];
}

export const FEATURE_GROUPS: FeatureGroup[] = [
  {
    id: "image-statistics",
    title: "Image Statistics",
    blurb:
      "Intensity distribution of the red channel. These describe the cover image itself rather than any embedding.",
    features: [
      {
        key: "r_mean",
        label: "Red Channel Mean",
        description: "Average intensity of the red channel.",
        digits: 3,
      },
      {
        key: "r_std",
        label: "Red Channel Standard Deviation",
        description: "Spread of red channel intensities around the mean.",
        digits: 3,
      },
      {
        key: "r_min",
        label: "Red Channel Minimum",
        description: "Darkest red value present in the image.",
        digits: 0,
      },
      {
        key: "r_max",
        label: "Red Channel Maximum",
        description: "Brightest red value present in the image.",
        digits: 0,
      },
    ],
  },
  {
    id: "lsb-statistics",
    title: "LSB Statistics",
    blurb:
      "Proportion of least-significant bits set to one. Balanced embedding tends to push these toward 0.5.",
    features: [
      {
        key: "r_lsb_ones_ratio",
        label: "Red LSB One Ratio",
        description: "Fraction of red-channel least-significant bits equal to 1.",
      },
      {
        key: "g_lsb_ones_ratio",
        label: "Green LSB One Ratio",
        description: "Fraction of green-channel least-significant bits equal to 1.",
      },
      {
        key: "b_lsb_ones_ratio",
        label: "Blue LSB One Ratio",
        description: "Fraction of blue-channel least-significant bits equal to 1.",
      },
      {
        key: "global_lsb_ones_ratio",
        label: "Global LSB One Ratio",
        description: "Fraction of least-significant bits equal to 1 across all channels.",
      },
    ],
  },
  {
    id: "transition-statistics",
    title: "Transition Statistics",
    blurb:
      "How often the LSB flips between neighbouring pixels. Embedded data raises the transition rate toward random.",
    features: [
      {
        key: "r_lsb_horizontal_transition_rate",
        label: "Red LSB Horizontal Transition Rate",
        description: "Rate at which the red LSB changes between horizontally adjacent pixels.",
      },
      {
        key: "r_lsb_vertical_transition_rate",
        label: "Red LSB Vertical Transition Rate",
        description: "Rate at which the red LSB changes between vertically adjacent pixels.",
      },
    ],
  },
  {
    id: "pair-statistics",
    title: "Pair Statistics",
    blurb:
      "Frequency of matching LSB pairs. Natural images show structure here that embedding disturbs.",
    features: [
      {
        key: "r_horizontal_pair_rate",
        label: "Red Horizontal Pair Rate",
        description: "Rate of equal LSB values in horizontally adjacent red pixels.",
      },
      {
        key: "r_vertical_pair_rate",
        label: "Red Vertical Pair Rate",
        description: "Rate of equal LSB values in vertically adjacent red pixels.",
      },
    ],
  },
  {
    id: "rs-analysis",
    title: "RS Analysis",
    blurb:
      "Regular / Singular group analysis, a classical LSB steganalysis statistic.",
    features: [
      {
        key: "r_rs_regular_ratio",
        label: "Red RS Regular Group Ratio",
        description: "Proportion of pixel groups classified as regular.",
      },
      {
        key: "r_rs_singular_ratio",
        label: "Red RS Singular Group Ratio",
        description: "Proportion of pixel groups classified as singular.",
      },
      {
        key: "r_rs_difference",
        label: "Red RS Difference",
        description: "Difference between the regular and singular group ratios.",
      },
    ],
  },
  {
    id: "sequential-lsb",
    title: "Sequential LSB Analysis",
    blurb:
      "Compares the start of the scan order against the remainder — sequential embedding leaves an imbalance.",
    features: [
      {
        key: "r_early_lsb_one_ratio",
        label: "Red Early LSB One Ratio",
        description: "LSB one-ratio measured over the earliest pixels in scan order.",
      },
      {
        key: "r_remaining_lsb_one_ratio",
        label: "Red Remaining LSB One Ratio",
        description: "LSB one-ratio measured over the remaining pixels.",
      },
      {
        key: "r_sequential_lsb_difference",
        label: "Red Sequential LSB Difference",
        description: "Difference between the early and remaining LSB one-ratios.",
      },
    ],
  },
];

const DESCRIPTOR_BY_KEY = new Map<string, FeatureDescriptor>(
  FEATURE_GROUPS.flatMap((group) =>
    group.features.map((feature) => [feature.key, feature] as const),
  ),
);

export function describeFeature(key: string): FeatureDescriptor {
  const known = DESCRIPTOR_BY_KEY.get(key);
  if (known) return known;

  // Any feature the model gains in future still renders sensibly.
  return {
    key,
    label: key
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" "),
    description: "Model feature.",
  };
}

/**
 * Split a feature map into the known groups, plus a catch-all group for
 * any feature the catalogue does not yet describe.
 */
export function groupFeatures(features: Record<string, number>) {
  const seen = new Set<string>();

  const groups = FEATURE_GROUPS.map((group) => {
    const entries = group.features
      .filter((feature) => feature.key in features)
      .map((feature) => {
        seen.add(feature.key);
        return { descriptor: feature, value: features[feature.key] };
      });

    return { ...group, entries };
  }).filter((group) => group.entries.length > 0);

  const extras = Object.keys(features)
    .filter((key) => !seen.has(key))
    .map((key) => ({ descriptor: describeFeature(key), value: features[key] }));

  if (extras.length) {
    groups.push({
      id: "other",
      title: "Other Features",
      blurb: "Additional features returned by the model.",
      features: extras.map((entry) => entry.descriptor),
      entries: extras,
    });
  }

  return groups;
}
