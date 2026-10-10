import { cn } from "@/lib/utils";
import type { ArgusState } from "@/hooks/use-argus-socket";

export function Reactor({ state }: { state: ArgusState }) {
  return (
    <div className={cn("reactor", `reactor-${state.toLowerCase()}`)} aria-label={`ARGUS state: ${state}`} role="img">
      <div className="reactor-orbit orbit-a" />
      <div className="reactor-orbit orbit-b" />
      <div className="reactor-spokes" />
      <div className="reactor-core"><span>J</span></div>
    </div>
  );
}
