import { useArgusStore } from "~/state/argusStore"

export function Notifications() {
  const { notifications, dismissNotification } = useArgusStore()

  return (
    <div className="argus-root fixed left-4 top-4 z-[2147483647] w-80 max-w-[calc(100vw-2rem)] space-y-2">
      {notifications.map((notification) => (
        <button
          key={notification.id}
          className="w-full border border-argus-line bg-white px-4 py-3 text-left text-sm shadow-argus"
          type="button"
          onClick={() => dismissNotification(notification.id)}
        >
          <span className="font-semibold capitalize">{notification.type}</span>
          <span className="block text-gray-700">{notification.message}</span>
        </button>
      ))}
    </div>
  )
}
