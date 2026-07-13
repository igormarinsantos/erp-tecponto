from tecponto_app.tecponto.requests import expire_requests


def expire_pending_requests():
	return expire_requests()
