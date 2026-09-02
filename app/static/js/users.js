const MAIN_ADMIN_EMAIL =
    "omar.qaisi735@gmail.com";


document.addEventListener(
    "DOMContentLoaded",
    async () => {

        if (!requireAuth()) {
            return;
        }


        const role =
            localStorage.getItem("role");

        const email =
            (
                localStorage.getItem("email")
                || ""
            ).toLowerCase();


        // Only Omar can open User Management
        if (
            role !== "admin"
            ||
            email !== MAIN_ADMIN_EMAIL.toLowerCase()
        ) {

            location.href = "/dashboard";

            return;
        }


        await loadUsers();
    }
);


async function loadUsers() {

    const body =
        document.getElementById(
            "usersBody"
        );


    try {

        const data = await API.request(
            APP_CONFIG.ENDPOINTS.users
        );


        const users =
            data.users || [];


        body.innerHTML =
            users.map(user => {

                const isMainAdmin =
                    user.Email.toLowerCase()
                    === MAIN_ADMIN_EMAIL.toLowerCase();


                if (isMainAdmin) {

                    return `
                        <tr>

                            <td>
                                #${user.ID}
                            </td>

                            <td>
                                ${esc(user.Full_Name)}
                            </td>

                            <td>
                                ${esc(user.Email)}
                            </td>

                            <td>
                                <strong>
                                    Admin
                                </strong>
                            </td>

                            <td>
                                ${esc(
                                    user.Created_At
                                    || "—"
                                )}
                            </td>

                            <td>
                                Main Admin
                            </td>

                        </tr>
                    `;
                }


                return `
                    <tr>

                        <td>
                            #${user.ID}
                        </td>

                        <td>
                            ${esc(user.Full_Name)}
                        </td>

                        <td>
                            ${esc(user.Email)}
                        </td>

                        <td>

                            <select
                                id="role-${user.ID}"
                            >

                                <option
                                    value="employee"
                                    ${
                                        user.Role === "employee"
                                        ? "selected"
                                        : ""
                                    }
                                >
                                    Employee
                                </option>

                                <option
                                    value="IT"
                                    ${
                                        user.Role === "IT"
                                        ? "selected"
                                        : ""
                                    }
                                >
                                    IT
                                </option>

                            </select>

                        </td>

                        <td>
                            ${esc(
                                user.Created_At
                                || "—"
                            )}
                        </td>

                        <td>

                            <button
                                class="btn"
                                data-email="${esc(user.Email)}"
                                onclick="changeRole(
                                    ${user.ID},
                                    this.dataset.email
                                )"
                            >
                                Save
                            </button>

                        </td>

                    </tr>
                `;

            }).join("")
            ||
            `
                <tr>

                    <td
                        colspan="6"
                        class="empty"
                    >
                        No users found
                    </td>

                </tr>
            `;

    }
    catch (e) {

        body.innerHTML = `
            <tr>

                <td
                    colspan="6"
                    class="empty"
                >
                    ${esc(e.message)}
                </td>

            </tr>
        `;
    }
}


async function changeRole(
    id,
    email
) {

    const select =
        document.getElementById(
            `role-${id}`
        );


    const role =
        select.value;


    try {

        await API.request(
            APP_CONFIG.ENDPOINTS.setRole,
            {

                method: "PUT",

                body: JSON.stringify({
                    email: email,
                    role: role
                })
            }
        );


        toast(
            "User role updated successfully"
        );


        await loadUsers();

    }
    catch (e) {

        toast(
            e.message,
            "error"
        );


        await loadUsers();
    }
}