import type { User } from '../types'

interface Props {
  user: User
  onLogout: () => void
}

function UserBar({ user, onLogout }: Props) {
  return (
    <div className="user-bar">
      <span>{user.username}</span>
      <button type="button" onClick={onLogout}>
        로그아웃
      </button>
    </div>
  )
}

export default UserBar
