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
    primary: "bg-primary text-primary-foreground hover:opacity-95",
    secondary: "bg-muted text-foreground hover:bg-muted/80",
    ghost: "bg-transparent text-foreground hover:bg-white/60",
    danger: "bg-rose-600 text-white hover:bg-rose-700",
  };

  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
