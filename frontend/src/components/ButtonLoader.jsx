import React from "react";
import { cn } from "../utils";

const ButtonLoader = ({ 
  loading = false, 
  children, 
  disabled = false,
  loadingText = "Loading...",
  className = "",
  loaderClassName = "",
  ...props 
}) => {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        "bg-brand-700 text-white hover:bg-brand-600 focus:ring-2 focus:ring-brand-500 focus:ring-offset-2",
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <div className={cn("w-4 h-4 animate-spin rounded-full border-2 border-white border-t-transparent", loaderClassName)} />
      )}
      {loading ? loadingText : children}
    </button>
  );
};

export default ButtonLoader;
