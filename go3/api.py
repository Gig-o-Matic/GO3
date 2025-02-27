from ninja import NinjaAPI

from gig.api import router as gig_router

api = NinjaAPI()

api.add_router("/gigs", gig_router)