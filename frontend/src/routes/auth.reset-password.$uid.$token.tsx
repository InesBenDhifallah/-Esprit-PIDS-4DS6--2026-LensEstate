import { createFileRoute } from "@tanstack/react-router";

// Support reset links that provide uid/token as path params:
// /auth/reset-password/:uid/:token
// This route just forwards to the existing styled reset page that expects search params.
export const Route = createFileRoute("/auth/reset-password/$uid/$token")({
  component: ForwardResetPasswordRoute,
});

function ForwardResetPasswordRoute() {
  const navigate = Route.useNavigate();
  const { uid, token } = Route.useParams();

  void navigate({
    to: "/auth/reset-password",
    search: { uid, token },
    replace: true,
  });

  return null;
}

