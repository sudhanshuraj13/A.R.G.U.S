import { useArgusStore } from "~/state/argusStore"

interface ApprovalModalProps {
  onApprove(id: string): void
  onReject(id: string): void
}

export function ApprovalModal({ onApprove, onReject }: ApprovalModalProps) {
  const approval = useArgusStore((state) => state.approvals[0])

  if (!approval) return null

  return (
    <div className="argus-root fixed inset-0 z-[2147483647] grid place-items-center bg-gray-950/35 p-4">
      <div className="w-full max-w-md border border-argus-line bg-white p-5 shadow-argus">
        <h2 className="text-base font-semibold">Approval Required</h2>
        <p className="mt-2 text-sm text-gray-700">{approval.reason}</p>
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
          {approval.action.description}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button className="rounded-md border border-argus-line px-3 py-2 text-sm" type="button" onClick={() => onReject(approval.id)}>
            Reject
          </button>
          <button className="rounded-md bg-argus-accent px-3 py-2 text-sm font-medium text-white" type="button" onClick={() => onApprove(approval.id)}>
            Approve
          </button>
        </div>
      </div>
    </div>
  )
}
