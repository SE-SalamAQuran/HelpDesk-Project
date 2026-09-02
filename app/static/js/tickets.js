let currentPage = 1;
const pageSize = 10;

document.addEventListener("DOMContentLoaded", () => {

    if (!requireAuth()) return;

    // Tickets list page
    if (document.getElementById("ticketsBody")) {

        loadTickets();

        prev.onclick = () => {
            if (currentPage > 1) {
                currentPage--;
                loadTickets();
            }
        };

        next.onclick = () => {
            currentPage++;
            loadTickets();
        };

        filterForm.onsubmit = e => {
            e.preventDefault();
            currentPage = 1;
            loadTickets(true);
        };

        clearFilters.onclick = () => {
            filterForm.reset();
            currentPage = 1;
            loadTickets();
        };
    }

    // Create ticket page
    if (document.getElementById("createTicketForm")) {
        createTicketForm.onsubmit = createTicket;
    }

    // Ticket details page
    if (
        window.CURRENT_TICKET_ID &&
        document.getElementById("ticketTitle")
    ) {
        loadDetail(CURRENT_TICKET_ID);
    }

    // Edit ticket page
    if (
        window.CURRENT_TICKET_ID &&
        document.getElementById("editTicketForm")
    ) {
        loadEdit(CURRENT_TICKET_ID);

        editTicketForm.onsubmit = e => {
            e.preventDefault();
            updateTicket(CURRENT_TICKET_ID);
        };
    }

    // Delete ticket
    if (document.getElementById("deleteTicket")) {

        deleteTicket.onclick = async () => {

            if (!confirm("Delete this ticket?")) return;

            try {

                await API.request(
                    APP_CONFIG.ENDPOINTS.ticketById(CURRENT_TICKET_ID),
                    {
                        method: "DELETE"
                    }
                );

                location.href = "/tickets";

            } catch (e) {
                toast(e.message, "error");
            }
        };
    }
});


async function loadTickets(search = false) {

    try {

        const q = new URLSearchParams({
            page: currentPage,
            per_page: pageSize
        });

        if (search) {

            if (window.q.value) {
                q.set("q", window.q.value);
            }

            if (status.value) {
                q.set("status", status.value);
            }

            if (priority.value) {
                q.set("priority", priority.value);
            }

            if (category.value) {
                q.set("category", category.value);
            }

            if (createdBy.value) {
                q.set("created_by", createdBy.value);
            }

            if (createdDate.value) {
                q.set("created_date", createdDate.value);
            }
        }

        const path =
            (
                search
                    ? APP_CONFIG.ENDPOINTS.ticketSearch
                    : APP_CONFIG.ENDPOINTS.getTickets
            )
            + "?"
            + q.toString();

        const d = await API.request(path);

        const tickets = Array.isArray(d)
            ? d
            : (d.tickets || d.data || []);

        ticketsBody.innerHTML =
            tickets.map(t => {

                const id = t.ID ?? t.id;

                return `
                    <tr>
                        <td>#${id}</td>

                        <td>
                            ${esc(t.Title ?? t.title)}
                        </td>

                        <td>
                            ${esc(t.Category ?? t.category)}
                        </td>

                        <td>
                            ${esc(t.Priority ?? t.priority)}
                        </td>

                        <td>
                            ${esc(t.Status ?? t.status)}
                        </td>

                        <td>
                            ${esc(t.Created_By ?? t.created_by)}
                        </td>

                        <td>
                            ${esc(
                                t.Assigned_To ??
                                t.assigned_to ??
                                "—"
                            )}
                        </td>

                        <td>
                            <a href="/tickets/${id}">
                                View
                            </a>
                        </td>
                    </tr>
                `;
            }).join("")
            ||
            `
                <tr>
                    <td colspan="8" class="empty">
                        No tickets found
                    </td>
                </tr>
            `;

        page.textContent =
            `Page ${d.page || currentPage}`;

        prev.disabled =
            currentPage <= 1;

        next.disabled =
            d.has_next === false ||
            tickets.length < pageSize;

    } catch (e) {

        ticketsBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty">
                    ${esc(e.message)}
                </td>
            </tr>
        `;
    }
}


async function createTicket(e) {

    e.preventDefault();

    try {

        const d = await API.request(
            APP_CONFIG.ENDPOINTS.createTicket,
            {
                method: "POST",

                body: JSON.stringify({

                    title:
                        document
                            .getElementById("title")
                            .value
                            .trim(),

                    description:
                        document
                            .getElementById("description")
                            .value
                            .trim(),

                    category:
                        document
                            .getElementById("category")
                            .value,

                    priority:
                        document
                            .getElementById("priority")
                            .value
                })
            }
        );


        const id =
            d.ID ??
            d.id ??
            d.ticket_id ??
            d.ticket?.ID ??
            d.ticket?.id;


        location.href =
            id
                ? `/tickets/${id}`
                : "/tickets";

    }

    catch (e) {

        toast(
            e.message,
            "error"
        );
    }
}


async function loadDetail(id) {

    try {

        const d = await API.request(
            APP_CONFIG.ENDPOINTS.ticketById(id)
        );

        const t =
            d.ticket ||
            d.data ||
            d;

        ticketTitle.textContent =
            t.Title ??
            t.title ??
            `Ticket #${id}`;

        ticketDescription.textContent =
            t.Description ??
            t.description ??
            "—";

        ticketCategory.textContent =
            t.Category ??
            t.category ??
            "—";

        ticketPriority.textContent =
            t.Priority ??
            t.priority ??
            "—";

        ticketStatus.textContent =
            t.Status ??
            t.status ??
            "—";

        ticketCreatedBy.textContent =
            t.Created_By ??
            t.created_by ??
            "—";

        ticketAssignedTo.textContent =
            t.Assigned_To ??
            t.assigned_to ??
            "Unassigned";

        ticketCreatedAt.textContent =
            t.Created_At ??
            t.created_at ??
            "—";

        ticketUpdatedAt.textContent =
            t.Updated_At ??
            t.updated_at ??
            "—";

    } catch (e) {

        toast(
            e.message,
            "error"
        );
    }
}


async function loadEdit(id) {

    try {

        const d = await API.request(
            APP_CONFIG.ENDPOINTS.ticketById(id)
        );

        const t =
            d.ticket ||
            d.data ||
            d;

        title.value =
            t.Title ??
            t.title ??
            "";

        description.value =
            t.Description ??
            t.description ??
            "";

        category.value =
            t.Category ??
            t.category ??
            "IT";

        priority.value =
            t.Priority ??
            t.priority ??
            "Medium";

        status.value =
            t.Status ??
            t.status ??
            "Open";

        assignedTo.value =
            t.Assigned_To ??
            t.assigned_to ??
            "";

    } catch (e) {

        toast(
            e.message,
            "error"
        );
    }
}


async function updateTicket(id) {
    try {
        await API.request(
            APP_CONFIG.ENDPOINTS.ticketById(id),
            {
                method: "PUT",
                body: JSON.stringify({
                    title: document.getElementById("title").value.trim(),
                    description: document.getElementById("description").value.trim(),
                    category: document.getElementById("category").value,
                    priority: document.getElementById("priority").value,
                    status: document.getElementById("status").value,
                    assigned_to: document.getElementById("assignedTo").value
                        ? Number(document.getElementById("assignedTo").value)
                        : null
                })
            }
        );

        location.href = `/tickets/${id}`;

    } catch (e) {
        toast(e.message, "error");
    }
}