"use client";

import Image from "next/image";
import { useState } from "react";
import { PlayIcon } from "@/components/icons";

type ClipCardProps = {
  youtube: string;
  poster: string;
  batter: string;
  result: string;
  detail: string;
};

/** Poster frame first, YouTube iframe only after a click, so the landing page
 *  doesn't pay for two embedded players nobody may watch. */
export function ClipCard({
  youtube,
  poster,
  batter,
  result,
  detail,
}: ClipCardProps) {
  const [playing, setPlaying] = useState(false);
  const label = `${batter}'s ${result.toLowerCase()}`;

  return (
    <figure className="overflow-hidden rounded-xl border border-ink/12 bg-paper">
      <div className="relative aspect-video bg-grass-900">
        {playing ? (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${youtube}?autoplay=1&rel=0`}
            title={label}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="absolute inset-0 size-full"
          />
        ) : (
          <button
            type="button"
            onClick={() => setPlaying(true)}
            aria-label={`Play the broadcast clip of ${label}`}
            className="group relative block size-full cursor-pointer focus-visible:outline-3 focus-visible:-outline-offset-3 focus-visible:outline-grass-500"
          >
            <Image
              src={poster}
              alt=""
              fill
              sizes="(min-width: 640px) 45vw, 92vw"
              className="object-cover"
            />
            <span className="absolute inset-0 bg-grass-900/15 transition group-hover:bg-grass-900/0" />
            <span className="absolute top-1/2 left-1/2 flex size-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-grass-700/95 text-chalk shadow-lg transition group-hover:scale-105 group-hover:bg-grass-700">
              <PlayIcon className="ml-0.5 size-6" />
            </span>
          </button>
        )}
      </div>

      <figcaption className="border-t border-ink/10 px-6 py-5">
        <p className="font-semibold text-ink">
          {batter} <span className="text-seam">{result}</span>
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-muted">{detail}</p>
      </figcaption>
    </figure>
  );
}
