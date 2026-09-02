window.APP_CONFIG = {
    API_BASE: "",

    ENDPOINTS: {
        signup: "/auth/signup",
        login: "/auth/login",
        resetPassword: "/auth/reset-password",
        googleSignin: "/auth/google-signin",
        profile: "/auth/profile",

        // Tickets
        getTickets: "/api/tickets",
        createTicket: "/tickets",
        ticketSearch: "/tickets/search",
        ticketById: id => `/tickets/${id}`,

        // Attachments
        uploadAttachment: id => `/attachments/upload/${id}`
    },

    GOOGLE_CLIENT_ID: "901061333603-08gj5dlulfhsk73pu4e6ok1gh17oe8mm.apps.googleusercontent.com"
};