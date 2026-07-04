// Central place for "which dashboard does this role land on" - used
// after login, after changing password, and by any "back to dashboard"
// link, so all three roles are handled consistently in one spot.
export function getDashboardPath(role) {
  if (role === "doctor") return "/doctor";
  if (role === "admin") return "/admin";
  return "/patient";
}
