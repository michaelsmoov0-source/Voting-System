import React from "react";
import { cn } from "../utils";

const LoadingOverlay = ({ 
  show = false, 
  text = "Loading...", 
  variant = "default",
  blur = true,
  spinnerSize = "lg",
  className = "",
  ...props 
}) => {
  if (!show) return null;

  const variantClasses = {
    default: "bg-white/90",
    dark: "bg-slate-900/90",
    light: "bg-slate-100/90",
    transparent: "bg-transparent",
  };

  return (
    <div 
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center",
        blur && "backdrop-blur-sm",
        variantClasses[variant],
        className
      )}
      {...props}
    >
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
        <p className="text-slate-700 font-medium">{text}</p>
      </div>
    </div>
  );
};

export default LoadingOverlay;
