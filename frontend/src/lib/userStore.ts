import {type Writable, writable} from "svelte/store";
import {browser} from "$app/environment";

interface LoggedInUser {
    username: string;
    token: string;
}

export const userStore: Writable<LoggedInUser | null> = writable(
    null,
    (set) => {
        if (!browser)
            return;

        const loggedInUser = localStorage.getItem("loggedInUser");
        if (loggedInUser) {
            set(JSON.parse(loggedInUser));
        }
    }
);

userStore.subscribe((value) => {
    if (!browser)
        return;

    localStorage.setItem("loggedInUser", JSON.stringify(value));
});
