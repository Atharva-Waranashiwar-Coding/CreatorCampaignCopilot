import { Link } from "react-router-dom";

import { formatDate, formatDateTime } from "../../lib/format";
import type { CalendarItem } from "../../lib/types";
import { Badge } from "../ui/badge";

type CampaignCalendarAgendaProps = {
  schedule: CalendarItem[];
};

export function CampaignCalendarAgenda({ schedule }: CampaignCalendarAgendaProps) {
  const groupedItems = schedule
    .slice()
    .sort((left, right) => left.scheduled_for.localeCompare(right.scheduled_for))
    .reduce<Array<{ date: string; items: CalendarItem[] }>>((groups, item) => {
      const date = item.scheduled_for.slice(0, 10);
      const existingGroup = groups.find((group) => group.date === date);

      if (existingGroup) {
        existingGroup.items.push(item);
        return groups;
      }

      groups.push({ date, items: [item] });
      return groups;
    }, []);

  if (!groupedItems.length) {
    return (
      <div className="rounded-[1.35rem] border border-dashed border-border bg-white/75 px-6 py-10 text-center">
        <p className="text-sm font-medium text-foreground">No scheduled items yet</p>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          Planned publish dates and campaign milestones will appear here once the team starts scheduling.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {groupedItems.map((group) => (
        <div key={group.date} className="rounded-[1.4rem] border border-border bg-white/85 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{formatDate(group.date)}</p>
              <h3 className="mt-2 text-lg font-semibold tracking-tight">{group.items.length} scheduled items</h3>
            </div>
            <Link className="text-sm font-medium text-primary" to="/calendar">
              Open full calendar
            </Link>
          </div>

          <div className="mt-4 space-y-3">
            {group.items.map((item) => (
              <Link
                key={item.id}
                className="block rounded-[1.2rem] border border-border bg-white px-4 py-4 transition hover:bg-slate-50/80"
                to={item.draft_id ? `/drafts/${item.draft_id}` : `/campaigns/${item.campaign_id}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h4 className="text-sm font-semibold text-foreground">{item.title}</h4>
                  <Badge tone={item.draft_id ? "success" : "muted"}>{item.item_type}</Badge>
                  {item.platform ? <Badge tone="muted">{item.platform}</Badge> : null}
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {formatDateTime(item.scheduled_for)}
                  {item.draft_title ? ` · ${item.draft_title}` : ""}
                </p>
                {item.notes ? <p className="mt-3 text-sm leading-6 text-foreground">{item.notes}</p> : null}
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
