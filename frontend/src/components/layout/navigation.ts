export type NavigationItem = {
  label: string;
  to: string;
  hint: string;
  sectionLabel: string;
  matchPrefixes?: string[];
};

export type NavigationSection = {
  label: string;
  items: NavigationItem[];
};

export const navigationSections: NavigationSection[] = [
  {
    label: "Overview",
    items: [
      {
        label: "Dashboard",
        to: "/",
        hint: "Health, workload, and risk in one view.",
        sectionLabel: "Overview",
      },
      {
        label: "Notifications",
        to: "/notifications",
        hint: "Unread updates, due soon work, and alerts.",
        sectionLabel: "Overview",
      },
    ],
  },
  {
    label: "Workspace",
    items: [
      {
        label: "Brands",
        to: "/brands",
        hint: "Workspace setup, roles, and brand rules.",
        sectionLabel: "Workspace",
      },
      {
        label: "Projects",
        to: "/projects",
        hint: "Campaign containers grouped by brand.",
        sectionLabel: "Workspace",
      },
      {
        label: "Campaigns",
        to: "/campaigns",
        hint: "Execution lanes, briefs, and launch timelines.",
        sectionLabel: "Workspace",
        matchPrefixes: ["/campaigns/"],
      },
      {
        label: "Calendar",
        to: "/calendar",
        hint: "Upcoming scheduled content and launch timing.",
        sectionLabel: "Workspace",
      },
    ],
  },
  {
    label: "Production",
    items: [
      {
        label: "Drafts",
        to: "/drafts",
        hint: "All working copy across campaigns and channels.",
        sectionLabel: "Production",
        matchPrefixes: ["/drafts/"],
      },
      {
        label: "Reviews",
        to: "/reviews",
        hint: "Items waiting on review and approval.",
        sectionLabel: "Production",
      },
      {
        label: "Templates",
        to: "/templates",
        hint: "Reusable structures for repeatable content.",
        sectionLabel: "Production",
      },
    ],
  },
  {
    label: "Intelligence",
    items: [
      {
        label: "AI Assist",
        to: "/tools",
        hint: "Helper tools, suggestions, and MCP activity.",
        sectionLabel: "Intelligence",
      },
      {
        label: "Billing",
        to: "/billing",
        hint: "Plan, usage, and upgrade controls.",
        sectionLabel: "Intelligence",
      },
    ],
  },
];

export const navigationItems = navigationSections.flatMap((section) => section.items);

export function getNavigationItem(pathname: string): NavigationItem | undefined {
  return navigationItems.find((item) => {
    if (item.to === pathname) {
      return true;
    }
    if (item.to !== "/" && pathname.startsWith(`${item.to}/`)) {
      return true;
    }
    return item.matchPrefixes?.some((prefix) => pathname.startsWith(prefix)) ?? false;
  });
}
