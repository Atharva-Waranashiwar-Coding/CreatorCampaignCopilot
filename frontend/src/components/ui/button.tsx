import type { ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/cn";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
};

export function Button({
  className,
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  const variants = {
    primary: "border border-primary/10 bg-primary text-primary-foreground shadow-[0_12px_26px_-18px_rgba(15,118,135,0.9)] hover:-translate-y-[1px] hover:opacity-95",
    secondary: "border border-slate-200 bg-white text-foreground shadow-sm hover:border-slate-300 hover:bg-slate-50",
    ghost: "border border-transparent bg-transparent text-foreground hover:border-slate-200 hover:bg-white/80",
    danger: "border border-rose-700/20 bg-rose-600 text-white shadow-[0_12px_26px_-18px_rgba(225,29,72,0.8)] hover:bg-rose-700",
  };

  return (
    <button
      type={type}
      className={cn(
        "inline-flex min-h-11 items-center justify-center rounded-[1rem] px-4 py-2 text-sm font-semibold transition duration-200 focus:outline-none focus:ring-2 focus:ring-primary/15 disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
