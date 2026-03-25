type EditorToolbarProps = {
  value: string;
  onInsert: (snippet: string) => void;
};

const editorActions = [
  {
    description: "Drop in a headline or opening hook.",
    label: "Hook",
    snippet: "Hook:\nLead with the outcome your audience will care about most.\n",
  },
  {
    description: "Create a structured list of points.",
    label: "Bullets",
    snippet: "- Point one\n- Point two\n- Point three\n",
  },
  {
    description: "Add a closing CTA block.",
    label: "CTA",
    snippet: "CTA:\nInvite the reader to book, click, reply, or share.\n",
  },
  {
    description: "Seed a hashtag cluster for social drafts.",
    label: "Hashtags",
    snippet: "#CreatorCampaign #LaunchPlan #ContentOps\n",
  },
  {
    description: "Insert a link placeholder.",
    label: "Link",
    snippet: "[Link text](https://example.com)\n",
  },
];

export function EditorToolbar({ onInsert, value }: EditorToolbarProps) {
  const characters = value.length;
  const words = value.trim() ? value.trim().split(/\s+/).length : 0;
  const lines = value ? value.split("\n").length : 0;
  const readingMinutes = Math.max(1, Math.ceil(words / 180));

  return (
    <div className="rounded-[1.25rem] border border-border bg-slate-50/80 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Editor tools</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Lightweight writing helpers that keep the composer fast while adding structure, rhythm, and reusable blocks.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <StatPill label="Words" value={words} />
          <StatPill label="Chars" value={characters} />
          <StatPill label="Lines" value={lines} />
          <StatPill label="Read" value={`${readingMinutes} min`} />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {editorActions.map((action) => (
          <button
            key={action.label}
            className="rounded-full bg-white px-4 py-2 text-sm font-medium text-foreground transition hover:bg-white/80"
            onClick={() => onInsert(action.snippet)}
            title={action.description}
            type="button"
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function StatPill({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-full bg-white px-3 py-1 text-xs font-medium text-muted-foreground">
      {label} · {value}
    </div>
  );
}
