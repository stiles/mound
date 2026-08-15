import type { MetadataRoute } from "next";
import { getExamples } from "@/lib/docs";
import { site } from "@/lib/site";

export const dynamic = "force-static";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const examples = await getExamples();

  return [
    { url: site.url, changeFrequency: "weekly", priority: 1 },
    { url: `${site.url}/examples`, changeFrequency: "monthly", priority: 0.8 },
    ...examples.map((example) => ({
      url: `${site.url}/examples/${example.slug}`,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
    { url: `${site.url}/changelog`, changeFrequency: "weekly", priority: 0.5 },
  ];
}
